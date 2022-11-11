def minify_teal(teal_lines):
    source_map = {}
    n = 1
    output = []
    previous_line_is_label = False
    previous_label = None
    label_replacements = {}
    for i, line in enumerate(teal_lines):
        i = i + 1
        line = line.strip()
        if not (not line or line.startswith("//")):
            if line.split("//")[0].strip().endswith(":"):
                label = line.split("//")[0].strip()[:-1]
                # duplicate labels get compressed into 1
                if previous_line_is_label:
                    label_replacements[label] = previous_label
                    continue
                previous_line_is_label = True
                previous_label = label
            else:
                previous_line_is_label = False
            source_map[n] = i
            n += 1
            output.append(line)
    source_map[n] = len(teal_lines) - 1
    for i, line in enumerate(output):
        for k in label_replacements:
            if k in line:
                output[i] = line.replace(k, label_replacements[k])
    return output, source_map


def combine_source_maps(teal_source_map, tealish_source_map):
    source_map = {}
    for i in teal_source_map:
        teal_line = teal_source_map[i]
        tealish_line = tealish_source_map[teal_line]
        source_map[i] = [teal_line, tealish_line]
    return source_map
