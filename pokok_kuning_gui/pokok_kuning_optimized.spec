# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# App code files - minimal essential
added_files = [
    ('model', 'model'),
    ('ui', 'ui'), 
    ('core', 'core'),
    ('utils', 'utils'),
]

# Add icon if exists
if os.path.exists('assets/img/logo.ico'):
    added_files.append(('assets/img/logo.ico', 'assets/img'))

def get_conda_prefix():
    """Get conda environment prefix"""
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix and os.path.exists(conda_prefix):
        return conda_prefix
    return None

def collect_essential_gdal_data():
    """Collect essential GDAL data for SHP export"""
    gdal_files = []
    conda_prefix = get_conda_prefix()
    
    if not conda_prefix:
        return gdal_files
    
    print(f"Collecting GDAL data from: {conda_prefix}")
    
    # Essential GDAL data files
    gdal_data_paths = [
        Path(conda_prefix) / "Library" / "share" / "gdal",
        Path(conda_prefix) / "share" / "gdal",
    ]
    
    essential_files = [
        'gcs.csv', 'pcs.csv', 'ellipsoid.csv', 'datum.csv', 'prime_meridian.csv'
    ]
    
    for gdal_path in gdal_data_paths:
        if gdal_path.exists():
            for data_file in essential_files:
                file_path = gdal_path / data_file
                if file_path.exists():
                    gdal_files.append((str(file_path), f"gdal_data/{data_file}"))
                    print(f"Found GDAL data: {data_file}")
            break
    
    # Essential PROJ data
    proj_data_paths = [
        Path(conda_prefix) / "Library" / "share" / "proj",
        Path(conda_prefix) / "share" / "proj",
    ]
    
    for proj_path in proj_data_paths:
        if proj_path.exists():
            # Just get a few essential proj files
            proj_files = list(proj_path.glob("*.db"))[:3]  # Get first 3 .db files
            for proj_file in proj_files:
                gdal_files.append((str(proj_file), f"proj_data/{proj_file.name}"))
                print(f"Found PROJ data: {proj_file.name}")
            break
    
    return gdal_files

def collect_essential_packages():
    """Collect essential package data for CUDA to work"""
    package_files = []
    
    # Torchvision package - CRITICAL for CUDA
    try:
        import torchvision
        torchvision_path = torchvision.__path__[0]
        package_files.append((torchvision_path, 'torchvision'))
        print(f"Added torchvision package: {torchvision_path}")
    except ImportError:
        print("Warning: torchvision not found")
    
    # PyTorch package - ensure CUDA support
    try:
        import torch
        torch_path = torch.__path__[0]
        package_files.append((torch_path, 'torch'))
        print(f"Added torch package: {torch_path}")
    except ImportError:
        print("Warning: torch not found")
    
    return package_files

# Collect GDAL data for SHP export
gdal_data = collect_essential_gdal_data()
added_files.extend(gdal_data)

# Collect essential packages for CUDA
package_data = collect_essential_packages()
added_files.extend(package_data)

# OPTIMIZED hidden imports - minimal but complete
hiddenimports = [
    # App modules
    'ui.main_window', 'core.processor', 'utils.config_manager',
    
    # FIXED PyTorch imports - include torch.distributed
    'torch', 'torch.cuda', 'torch._C', 'torch.nn',
    'torch.distributed',           # CRITICAL FIX
    'torch.distributed.nn',        # Also needed
    'torch.utils', 'torch.utils.data',
    'torch.backends', 'torch.backends.cuda', 'torch.backends.cudnn',
    'torch.version',
    
    # Torchvision - needed for CUDA to work properly
    'torchvision', 'torchvision.transforms', 'torchvision.models',
    'torchvision.models.resnet', 'torchvision.models.vgg',
    
    # FIXED Ultralytics essentials - MINIMAL but COMPLETE
    'ultralytics', 'ultralytics.models', 'ultralytics.models.yolo',
    'ultralytics.models.yolo.detect', 'ultralytics.models.yolo.detect.predict',
    'ultralytics.models.yolo.detect.val', 'ultralytics.models.yolo.detect.train',
    'ultralytics.models.yolo.segment', 'ultralytics.models.yolo.classify',
    'ultralytics.models.rtdetr',   # NEEDED for Ultralytics initialization
    'ultralytics.models.sam',      # NEEDED - was causing import error
    'ultralytics.engine', 'ultralytics.engine.predictor', 'ultralytics.engine.results',
    'ultralytics.engine.trainer', 'ultralytics.engine.validator',
    'ultralytics.utils', 'ultralytics.utils.plotting', 'ultralytics.utils.ops',
    'ultralytics.utils.torch_utils', 'ultralytics.utils.checks',
    'ultralytics.data', 'ultralytics.data.utils', 'ultralytics.data.base',
    'ultralytics.nn', 'ultralytics.nn.modules', 'ultralytics.nn.tasks',
    'ultralytics.trackers', 'ultralytics.trackers.track',
    
    # Computer Vision - minimal essential
    'cv2', 'numpy', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
    
    # Additional essential modules for stability
    'yaml', 'tqdm', 'requests', 'urllib3',
    
    # Pandas modules - needed for geopandas
    'pandas', 'pandas.core', 'pandas.core.api', 'pandas.core.frame', 'pandas.core.series',
    'pandas.core.groupby', 'pandas.core.groupby.generic',
    
    # Geospatial for SHP/KML export - minimal essential
    'geojson', 'shapely', 'shapely.geometry', 'shapely.ops',
    'geopandas', 'geopandas.io', 'geopandas.io.file',
    'fiona', 'fiona.io', 'fiona.crs', 'fiona.schema', 'fiona.env',
    'pyproj', 'pyproj.crs', 'osgeo', 'osgeo.gdal', 'osgeo.ogr', 'osgeo.osr',
    
    # PyQt5 - minimal essential
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip',
    
    # System essentials - minimal
    'threading', 'multiprocessing', 'concurrent.futures',
    'logging', 'json', 'pathlib', 'time', 'gc', 'traceback',
]

print(f"Optimized hidden imports: {len(hiddenimports)}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-optimized.py'],
    excludes=[
        # Exclude heavy non-essential modules
        'tkinter', 'matplotlib.pyplot', 'scipy.optimize', 'sklearn.datasets',
        'IPython', 'jupyter', 'notebook',
        'setuptools', 'distutils', 'wheel', 'pip',
        # Exclude heavy plotting and visualization
        'matplotlib', 'seaborn', 'plotly', 'bokeh',
        # Exclude heavy scientific computing
        'scipy.spatial', 'scipy.stats', 'scipy.optimize',
        # Exclude heavy ML libraries
        'sklearn', 'tensorflow', 'keras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter data files - keep essential only
filtered_datas = []
for data_tuple in a.datas:
    if len(data_tuple) >= 2:
        src_path = data_tuple[0].lower()
        
        # Skip patterns
        skip_patterns = [
            'test/', 'tests/', 'example/', 'examples/', 'doc/', 'docs/',
            'sample/', 'samples/', 'demo/', 'demos/', 'tutorial/',
            '.md', '.rst', '.txt', 'readme', 'changelog', 'license',
            'benchmark/', 'profiling/', '.pyi', '.typed',
        ]
        
        should_skip = any(pattern in src_path for pattern in skip_patterns)
        
        if not should_skip:
            filtered_datas.append(data_tuple)

a.datas = filtered_datas
print(f"Filtered data files: {len(a.datas)}")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PokokKuningApp',
    debug=False,              # Disable debug for production
    bootloader_ignore_signals=False,
    strip=False,                     # Keep disabled to avoid warnings
    upx=True,                        # Compress for size
    console=True,                    # Keep console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/img/logo.ico' if os.path.exists('assets/img/logo.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'cudart*.dll', 'cublas*.dll', 'c10_cuda.dll',
        'gdal*.dll', 'proj*.dll', 'geos*.dll'
    ],
    name='PokokKuningApp',
)
