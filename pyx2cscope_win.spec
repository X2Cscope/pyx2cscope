# -*- mode: python ; coding: utf-8 -*-
# Created from command:
#  pyinstaller --add-data pyx2cscope\gui\web\static:pyx2cscope\gui\web\static --add-data pyx2cscope\gui\web\templates:pyx2cscope\gui\web\templates --add-data pyx2cscope\gui\img:pyx2cscope\gui\img --name pyX2Cscope --icon pyx2cscope\gui\img\pyx2cscope.ico .\pyx2cscope\__main__.py 

a = Analysis(
    ['pyx2cscope\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('pyx2cscope\\gui\\web\\static', 'pyx2cscope\\gui\\web\\static'), ('pyx2cscope\\gui\\web\\templates', 'pyx2cscope\\gui\\web\\templates'), ('pyx2cscope\\gui\\img', 'pyx2cscope\\gui\\img')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pyX2Cscope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pyx2cscope\\gui\\img\\pyx2cscope.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pyX2Cscope',
)
