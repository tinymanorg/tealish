def minify_teal(teal_lines):
    source_map = {}
    n = 1
    output = []
    previous_line_is_label = False
    for i, line in enumerate(teal_lines):
        i = i + 1
        line = line.strip()
        if not (not line or line.startswith("//")):
            if line.split("//")[0].strip().endswith(":"):
                # duplicate labels get compressed into 1
                if previous_line_is_label:
                    continue
                previous_line_is_label = True
            else:
                previous_line_is_label = False
            source_map[n] = i
            n += 1
            output.append(line)
    source_map[n] = len(teal_lines) - 1
    return output, source_map


def combine_source_maps(teal_source_map, tealish_source_map):
    source_map = {}
    for i in teal_source_map:
        teal_line = teal_source_map[i]
        tealish_line = tealish_source_map[teal_line]
        source_map[i] = [teal_line, tealish_line]
    return source_map
