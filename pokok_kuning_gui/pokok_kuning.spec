# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Data files yang perlu diinclude
datas = [
    ('model/yolov8n-pokok-kuning.pt', 'model'),
    ('ui', 'ui'),
    ('utils', 'utils'),
    ('core', 'core'),
]

# Hidden imports yang diperlukan
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'ultralytics',
    'ultralytics.yolo',
    'ultralytics.yolo.v8',
    'ultralytics.yolo.v8.detect',
    'ultralytics.yolo.v8.segment',
    'ultralytics.yolo.v8.classify',
    'ultralytics.yolo.v8.pose',
    'ultralytics.yolo.utils',
    'ultralytics.yolo.utils.ops',
    'ultralytics.yolo.utils.plotting',
    'ultralytics.yolo.utils.torch_utils',
    'ultralytics.yolo.utils.checks',
    'ultralytics.yolo.utils.files',
    'ultralytics.yolo.utils.tal',
    'ultralytics.yolo.utils.loss',
    'ultralytics.yolo.utils.metrics',
    'numpy',
    'cv2',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'geojson',
    'shapely',
    'shapely.geometry',
    'shapely.ops',
    'fastkml',
    'geopandas',
    'tqdm',
    'sqlite3',
    'json',
    'os',
    'sys',
    'pathlib',
    'datetime',
    'time',
    'threading',
    'queue',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pokok_Kuning_Desktop_App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False untuk GUI app (tidak ada console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pokok_Kuning_Desktop_App',
)
