from algosdk import source_map


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


def strip_comments(teal_lines):
    output = []
    for i, line in enumerate(teal_lines):
        line = line.strip()
        if not (not line or line.startswith("//")):
            line = line.split("//")[0].strip()
            output.append(line)
    return output


class TealishMap:
    def __init__(self, map=None) -> None:
        map = map or {}
        self.pc_teal = {int(k): int(v) for k, v in map.get("pc_teal", {}).items()}
        self.teal_tealish = {
            int(k): int(v) for k, v in map.get("teal_tealish", {}).items()
        }
        self.errors = {int(k): v for k, v in map.get("errors", {}).items()}
        self.tealish_teal = {}
        for teal, tealish in self.teal_tealish.items():
            if tealish not in self.tealish_teal:
                self.tealish_teal[tealish] = []
            self.tealish_teal[tealish].append(teal)

    def get_tealish_line_for_pc(self, pc):
        teal_line = self.get_teal_line_for_pc(pc)
        return self.teal_tealish.get(teal_line, None)

    def get_teal_line_for_pc(self, pc):
        return self.pc_teal.get(pc, None)

    def get_teal_lines_for_tealish(self, tealish_line):
        return self.tealish_teal.get(tealish_line, [])

    def get_tealish_line_for_teal(self, teal_line):
        return self.teal_tealish.get(teal_line, None)

    def get_error_for_pc(self, pc):
        tealish_line = self.get_tealish_line_for_pc(pc)
        return self.errors.get(tealish_line, None)

    def update_from_teal_sourcemap(self, sourcemap):
        if type(sourcemap) == dict:
            sourcemap = source_map.SourceMap(sourcemap)
        self.pc_teal = dict(sourcemap.pc_to_line)

    def as_dict(self):
        return {
            "pc_teal": self.pc_teal,
            "teal_tealish": self.teal_tealish,
            "errors": self.errors,
        }
