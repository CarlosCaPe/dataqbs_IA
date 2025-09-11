import os, shutil
SRC = r'c:\Users\Lenovo\dataqbs_IA\emails_out\Gmail_dataqbs\Suspicious'
DST = r'c:\Users\Lenovo\dataqbs_IA\emails_out\Gmail_dataqbs\Sus'
count=0
if os.path.isdir(SRC):
    for name in os.listdir(SRC):
        if not name.lower().endswith('.eml'): continue
        new_name = name.replace('Suspicious','Sus')
        src_path = os.path.join(SRC,name)
        dst_path = os.path.join(DST,new_name)
        if os.path.exists(dst_path):
            os.remove(src_path)
        else:
            shutil.move(src_path,dst_path)
            count+=1
    try:
        os.rmdir(SRC)
    except OSError:
        pass
print(f'Migrated {count} files.')
