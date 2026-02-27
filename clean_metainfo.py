"""Remove the 3 remaining garbage entries."""
filepath = r'C:\Users\rahul\Downloads\NPDC_COPY\metainfo_23_feb2026.sql'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines at indices (0-based): 160208, 160216, 266144
# But indices shift after removal, so collect line numbers and filter
remove_lines = {160209, 160217, 266145}  # 1-indexed from output

clean_lines = [line for i, line in enumerate(lines) if (i+1) not in remove_lines]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print(f"Removed 3 remaining entries. Lines: {len(lines)} -> {len(clean_lines)}")

# Final verify
garbage_keywords = ['test', 'hii', 'sdfsadf', 'sfcac', 'ictd', 'sample']
found = 0
for line in clean_lines:
    parts = line.split('\t')
    if len(parts) > 2:
        title = parts[2].strip().lower()
        for kw in garbage_keywords:
            if kw in title and len(title) < 80:
                found += 1
                print(f"  Still found: {parts[2].strip()}")
                break

if found == 0:
    print("✅ ALL garbage entries have been removed!")
