import sys

in_file = open(sys.argv[1], 'r')
lines = in_file.readlines()
filtered_lines = list()
for line in lines:
    filtered_lines.append(bytes(line, 'utf-8').decode('utf-8','ignore'))
in_file.close()
out_file = open(sys.argv[1], 'w')
out_file.writelines(filtered_lines)
out_file.close()
