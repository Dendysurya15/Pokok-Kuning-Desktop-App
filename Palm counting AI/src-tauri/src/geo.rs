//! TFW/JGW, GeoJSON, KML, Shapefile.

use geojson::{Feature, FeatureCollection, GeoJson, Geometry, Value};
use shapefile::record::Point as ShpPoint;
use shapefile::Writer as ShpWriter;
use std::path::Path;

/// TFW params: pixel_size_x, rotation_x, rotation_y, pixel_size_y, upper_left_x, upper_left_y.
#[derive(Debug, Clone)]
pub struct TfwParams([f64; 6]);

impl TfwParams {
    pub fn pixel_size_x(&self) -> f64 {
        self.0[0]
    }
    pub fn pixel_size_y(&self) -> f64 {
        self.0[3]
    }
    pub fn upper_left_x(&self) -> f64 {
        self.0[4]
    }
    pub fn upper_left_y(&self) -> f64 {
        self.0[5]
    }
}

pub fn read_tfw(path: &Path) -> Option<TfwParams> {
    let s = std::fs::read_to_string(path).ok()?;
    let mut out = [0.0_f64; 6];
    for (i, line) in s.lines().take(6).enumerate() {
        out[i] = line.trim().parse().ok()?;
    }
    Some(TfwParams(out))
}

/// Pixel (center) to map coords. Same as processor `image_to_map_coords`.
pub fn pixel_to_map(cx: f64, cy: f64, p: &TfwParams) -> (f64, f64) {
    let map_x = p.upper_left_x() + cx * p.pixel_size_x();
    let map_y = p.upper_left_y() + cy * p.pixel_size_y();
    (map_x, map_y)
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Detection {
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
    pub class_id: i64,
    pub conf: f64,
}

impl Detection {
    fn center(&self) -> (f64, f64) {
        let cx = (self.x1 + self.x2) / 2.0;
        let cy = (self.y1 + self.y2) / 2.0;
        (cx, cy)
    }
}

fn label(class_id: i64) -> String {
    format!("class_{}", class_id)
}

/// Build GeoJSON FeatureCollection from detections + TFW.
pub fn create_geojson(detections: &[Detection], tfw: &TfwParams) -> FeatureCollection {
    let features: Vec<Feature> = detections
        .iter()
        .map(|d| {
            let (cx, cy) = d.center();
            let (map_x, map_y) = pixel_to_map(cx, cy, tfw);
            let geom = Geometry::new(Value::Point(vec![map_x, map_y]));
            let mut props = serde_json::Map::new();
            props.insert("label".into(), serde_json::json!(label(d.class_id)));
            props.insert("confidence".into(), serde_json::json!(d.conf));
            props.insert("class_id".into(), serde_json::json!(d.class_id));
            Feature {
                bbox: None,
                geometry: Some(geom),
                id: None,
                properties: Some(props),
                foreign_members: None,
            }
        })
        .collect();
    FeatureCollection {
        bbox: None,
        features,
        foreign_members: None,
    }
}

/// Save FeatureCollection to path. Uses stem of image_path for filename.
pub fn save_geojson(fc: &FeatureCollection, image_path: &Path, out_dir: &Path) -> Option<std::path::PathBuf> {
    let stem = image_path.file_stem()?.to_str()?;
    let mut out = out_dir.join(format!("{}.geojson", stem));
    let mut n = 0u32;
    while out.exists() {
        n += 1;
        out = out_dir.join(format!("{}_{}.geojson", stem, n));
    }
    let json = GeoJson::from(geojson::FeatureCollection::clone(fc));
    std::fs::write(&out, json.to_string()).ok()?;
    Some(out)
}

/// Write KML to `kml_path`. Uses same logic as GeoJSON (detections + tfw).
pub fn write_kml(detections: &[Detection], tfw: &TfwParams, kml_path: &Path) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut placemarks = String::new();
    for d in detections {
        let (cx, cy) = d.center();
        let (mx, my) = pixel_to_map(cx, cy, tfw);
        let lab = label(d.class_id);
        placemarks.push_str(&format!(
            r#"<Placemark><name>{}</name><Point><coordinates>{},{}</coordinates></Point></Placemark>"#,
            html_escape(&lab),
            mx,
            my
        ));
    }
    let kml = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><name>Palm detections</name>
{}
</Document>
</kml>"#,
        placemarks
    );
    std::fs::write(kml_path, kml)?;
    Ok(())
}

fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

/// Write shapefile to `shp_path` (e.g. "out/foo.shp"). Creates .shp, .shx, .dbf.
pub fn write_shp(
    detections: &[Detection],
    tfw: &TfwParams,
    shp_path: &Path,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use dbase::TableWriterBuilder;
    use std::convert::TryInto;

    let table_builder = TableWriterBuilder::new()
        .add_character_field("label".try_into().unwrap(), 64)
        .add_numeric_field("confidence".try_into().unwrap(), 10, 6)
        .add_numeric_field("class_id".try_into().unwrap(), 4, 0);

    let mut writer = ShpWriter::from_path(shp_path, table_builder)?;

    for d in detections {
        let (cx, cy) = d.center();
        let (mx, my) = pixel_to_map(cx, cy, tfw);
        let pt = ShpPoint::new(mx, my);
        let mut rec = dbase::Record::default();
        rec.insert("label".to_string(), dbase::FieldValue::Character(Some(label(d.class_id))));
        rec.insert(
            "confidence".to_string(),
            dbase::FieldValue::Numeric(Some(d.conf)),
        );
        rec.insert(
            "class_id".to_string(),
            dbase::FieldValue::Numeric(Some(d.class_id as f64)),
        );
        writer.write_shape_and_record(&pt, &rec)?;
    }
    Ok(())
}
