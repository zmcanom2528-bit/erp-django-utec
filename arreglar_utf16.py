import pathlib

for p in pathlib.Path('.').rglob('*.py'):
    if 'env_erp' in p.parts or 'env_erp_roto' in p.parts:
        continue
    datos = p.read_bytes()
    if b'\x00' not in datos:
        continue
    try:
        if datos.startswith((b'\xff\xfe', b'\xfe\xff')):
            texto = datos.decode('utf-16')
        else:
            texto = datos.decode('utf-16-le')
        p.write_bytes(texto.encode('utf-8'))
        print('CONVERTIDO a UTF-8:', p)
    except UnicodeDecodeError:
        print('NO SE PUEDE CONVERTIR (restaura con git):', p)