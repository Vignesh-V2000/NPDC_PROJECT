import pathlib

path = pathlib.Path(r"c:\Users\rahul\Downloads\NPDC_PROJECT\data_submission\views.py")
# read with latin1 to avoid decoding errors or use errors='ignore'
text = path.read_text(encoding='utf-8', errors='ignore')
lines = text.splitlines(keepends=True)
out_lines = []
comment = False
for line in lines:
    # start commenting once we hit either of the two request-related functions
    if line.startswith('def admin_approve_data_request') or line.startswith('def admin_reject_data_request'):
        comment = True
    if comment:
        out_lines.append('# ' + line)
    else:
        out_lines.append(line)
# write back
path.write_text(''.join(out_lines), encoding='utf-8')
print("approval/rejection functions commented out")
