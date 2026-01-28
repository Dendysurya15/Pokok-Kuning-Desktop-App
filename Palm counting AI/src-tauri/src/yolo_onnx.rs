//! ONNX-based YOLO inference using ort (ONNX Runtime).

use crate::geo::Detection;
use image::{DynamicImage, GenericImageView, Rgb, RgbImage};
use ndarray::Array4;
use ort::{
    ep::{CUDA, CPU},
    session::Session,
    value::Tensor,
    inputs,
};
use std::path::Path;
use std::sync::Mutex;

pub struct YOLOInference {
    session: Mutex<Session>,
    imgsz: u32,
}

impl YOLOInference {
    /// Load ONNX model and create inference engine
    pub fn new(onnx_path: &Path, imgsz: u32) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        // Try CUDA first, fallback to CPU
        let session = Session::builder()?
            .with_execution_providers([
                CUDA::default().build(),
                CPU::default().build(),
            ])?
            .commit_from_file(onnx_path)?;

        Ok(Self {
            session: Mutex::new(session),
            imgsz,
        })
    }

    /// Run inference on image
    pub fn predict(
        &self,
        img: &DynamicImage,
        conf_threshold: f32,
        iou_threshold: f32,
        max_detections: i32,
    ) -> Result<Vec<Detection>, Box<dyn std::error::Error + Send + Sync>> {
        // 1. Preprocess image (returns padding info for scaling back)
        let (input_tensor, pad_x, pad_y, scale) = self.preprocess_with_padding(img)?;

        // 2. Run inference
        let inputs_map = inputs!["images" => input_tensor];
        let mut session = self.session.lock().map_err(|e| format!("Failed to lock session: {}", e))?;
        let outputs = session.run(inputs_map)?;

        // 3. Extract output tensor
        let output_value = outputs.get("output0")
            .ok_or("Missing output0 in model outputs")?;
        
        // Extract as tensor (returns shape and data slice)
        let (shape, data) = output_value
            .try_extract_tensor::<f32>()
            .map_err(|e| format!("Failed to extract tensor: {:?}", e))?;
        
        // Convert to ndarray for processing
        // Shape is [batch, num_detections, num_values]
        let dims: Vec<usize> = shape.iter().map(|&d| d as usize).collect();
        if dims.len() < 3 {
            return Err("Invalid output shape".into());
        }
        
        // Create ndarray from slice
        let output = ndarray::ArrayViewD::from_shape(
            &dims[..],
            data
        ).map_err(|e| format!("Failed to create array view: {}", e))?;

        // 4. Post-process (decode boxes, apply NMS, scale back to original image)
        let detections = self.post_process(
            output,
            img.width() as f32,
            img.height() as f32,
            pad_x,
            pad_y,
            scale,
            conf_threshold,
            iou_threshold,
            max_detections,
        )?;

        Ok(detections)
    }

    /// Preprocess image: resize, normalize, convert to tensor
    /// Returns (tensor, pad_x, pad_y, scale) for post-processing
    fn preprocess_with_padding(
        &self,
        img: &DynamicImage,
    ) -> Result<(Tensor<f32>, f32, f32, f32), Box<dyn std::error::Error + Send + Sync>> {
        // Convert to RGB if needed
        let rgb_img = img.to_rgb8();

        // Resize with letterbox (maintain aspect ratio)
        let (resized, pad_x, pad_y, scale) = self.letterbox_resize(&rgb_img, self.imgsz);

        // Normalize: /255.0, then convert to CHW format
        let mut array = Array4::<f32>::zeros((1, 3, self.imgsz as usize, self.imgsz as usize));

        for y in 0..self.imgsz as usize {
            for x in 0..self.imgsz as usize {
                let pixel = resized.get_pixel(x as u32, y as u32);
                array[[0, 0, y, x]] = pixel[0] as f32 / 255.0; // R
                array[[0, 1, y, x]] = pixel[1] as f32 / 255.0; // G
                array[[0, 2, y, x]] = pixel[2] as f32 / 255.0; // B
            }
        }

        // Convert to ort::Tensor using from_array
        let tensor = Tensor::from_array(array)?;
        Ok((tensor, pad_x, pad_y, scale))
    }

    /// Letterbox resize: maintain aspect ratio, pad with gray
    fn letterbox_resize(
        &self,
        img: &RgbImage,
        target_size: u32,
    ) -> (RgbImage, f32, f32, f32) {
        let (w, h) = img.dimensions();
        let scale = (target_size as f32 / w.max(h) as f32).min(1.0);
        let new_w = (w as f32 * scale) as u32;
        let new_h = (h as f32 * scale) as u32;

        let resized = image::imageops::resize(img, new_w, new_h, image::imageops::FilterType::Lanczos3);
        
        // Create padded image
        let mut padded = RgbImage::new(target_size, target_size);
        // Fill with gray (114, 114, 114) - YOLO standard
        for pixel in padded.pixels_mut() {
            *pixel = Rgb([114, 114, 114]);
        }

        // Center the resized image
        let pad_x = (target_size - new_w) / 2;
        let pad_y = (target_size - new_h) / 2;
        
        for y in 0..new_h {
            for x in 0..new_w {
                let pixel = resized.get_pixel(x, y);
                padded.put_pixel(x + pad_x, y + pad_y, *pixel);
            }
        }

        (padded, pad_x as f32, pad_y as f32, scale)
    }

    /// Post-process: decode boxes, apply NMS, filter by confidence
    /// YOLOv8 ONNX output format: [batch, 8400, 84] where 84 = 4 (xywh normalized) + 80 class scores
    fn post_process(
        &self,
        output: ndarray::ArrayViewD<'_, f32>,
        img_width: f32,
        img_height: f32,
        pad_x: f32,
        pad_y: f32,
        scale: f32,
        conf_threshold: f32,
        iou_threshold: f32,
        max_detections: i32,
    ) -> Result<Vec<Detection>, Box<dyn std::error::Error + Send + Sync>> {
        let shape = output.shape();
        if shape.len() < 3 {
            return Ok(vec![]);
        }

        let num_detections = shape[1];
        let num_values = shape[2];

        let mut detections = Vec::new();

        // YOLOv8 ONNX format: [batch, 8400, 84]
        // Values: [x_center_norm, y_center_norm, width_norm, height_norm, class0_score, class1_score, ...]
        // All coordinates are normalized to [0, 1] relative to input image size (imgsz x imgsz)
        
        for i in 0..num_detections {
            if num_values < 4 {
                continue;
            }

            // Extract normalized box coordinates (use get() for safe indexing)
            let x_center_norm = *output.get([0, i, 0]).unwrap_or(&0.0) as f64;
            let y_center_norm = *output.get([0, i, 1]).unwrap_or(&0.0) as f64;
            let width_norm = *output.get([0, i, 2]).unwrap_or(&0.0) as f64;
            let height_norm = *output.get([0, i, 3]).unwrap_or(&0.0) as f64;

            // Find max class score and class_id
            let mut max_conf = 0.0;
            let mut max_class = 0i64;
            for c in 4..num_values {
                if let Some(&score) = output.get([0, i, c]) {
                    let score = score as f64;
                    if score > max_conf {
                        max_conf = score;
                        max_class = (c - 4) as i64;
                    }
                }
            }

            // Filter by confidence
            if max_conf < conf_threshold as f64 {
                continue;
            }

            // Convert normalized coordinates to pixel coordinates (on input image size)
            let x_center = x_center_norm * self.imgsz as f64;
            let y_center = y_center_norm * self.imgsz as f64;
            let width = width_norm * self.imgsz as f64;
            let height = height_norm * self.imgsz as f64;

            // Convert center+size to x1,y1,x2,y2
            let mut x1 = x_center - width / 2.0;
            let mut y1 = y_center - height / 2.0;
            let mut x2 = x_center + width / 2.0;
            let mut y2 = y_center + height / 2.0;

            // Remove padding and scale back to original image size
            x1 = (x1 - pad_x as f64) / scale as f64;
            y1 = (y1 - pad_y as f64) / scale as f64;
            x2 = (x2 - pad_x as f64) / scale as f64;
            y2 = (y2 - pad_y as f64) / scale as f64;

            // Clamp to image bounds
            x1 = x1.max(0.0).min(img_width as f64);
            y1 = y1.max(0.0).min(img_height as f64);
            x2 = x2.max(0.0).min(img_width as f64);
            y2 = y2.max(0.0).min(img_height as f64);

            // Skip invalid boxes
            if x2 <= x1 || y2 <= y1 {
                continue;
            }

            detections.push(Detection {
                x1,
                y1,
                x2,
                y2,
                class_id: max_class,
                conf: max_conf,
            });
        }

        // Apply NMS (Non-Max Suppression)
        let detections = self.nms(detections, iou_threshold as f64, max_detections as usize);

        Ok(detections)
    }

    /// Non-Max Suppression to remove overlapping boxes
    fn nms(
        &self,
        mut detections: Vec<Detection>,
        iou_threshold: f64,
        max_detections: usize,
    ) -> Vec<Detection> {
        if detections.is_empty() {
            return detections;
        }

        // Sort by confidence (descending)
        detections.sort_by(|a, b| b.conf.partial_cmp(&a.conf).unwrap_or(std::cmp::Ordering::Equal));

        let mut selected = Vec::new();
        let mut remaining = detections;

        while !remaining.is_empty() && selected.len() < max_detections {
            // Take the highest confidence detection
            let best = remaining.remove(0);
            selected.push(best.clone());

            // Remove all detections with high IoU overlap
            remaining.retain(|det| {
                let iou = self.calculate_iou(&best, det);
                iou < iou_threshold
            });
        }

        selected
    }

    /// Calculate IoU (Intersection over Union) between two boxes
    fn calculate_iou(&self, box1: &Detection, box2: &Detection) -> f64 {
        let x1 = box1.x1.max(box2.x1);
        let y1 = box1.y1.max(box2.y1);
        let x2 = box1.x2.min(box2.x2);
        let y2 = box1.y2.min(box2.y2);

        if x2 <= x1 || y2 <= y1 {
            return 0.0;
        }

        let intersection = (x2 - x1) * (y2 - y1);
        let area1 = (box1.x2 - box1.x1) * (box1.y2 - box1.y1);
        let area2 = (box2.x2 - box2.x1) * (box2.y2 - box2.y1);
        let union = area1 + area2 - intersection;

        if union <= 0.0 {
            return 0.0;
        }

        intersection / union
    }
}
