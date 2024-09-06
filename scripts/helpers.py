from enum import Enum, auto
import re

# RegEx patterns
AUTHOR_CHARS = r"a-zA-Zßğö.\/_"
AUTHOR_REGEX = fr"(?<!OG )(?!OG )\b(?:van|[A-Z])[{AUTHOR_CHARS} ]+"
YEAR_REGEX = r"\d{4}[a-z]?"
BEGIN_INFO_REGEX = r"(?!al)[a-zA-Z]+\."  # To avoid matching "et al."
NUM_INFO_REGEX = r"(?:[A-Z\d\.]+(?:, |-))*[A-Z\d\.]+"
PREFIX_REGEX = r"\(|[a-z;] "
# Generated by ChatGPT
SPLIT_REGEX = r',(?!(?:[^()]*\([^()]*\))*[^()]*\)) '

# Used in multiple files
class Rigidity(Enum):
    EXP = auto()
    IMP = auto()

def getSources(s):
    sources = re.findall(fr"\{{({AUTHOR_REGEX})({YEAR_REGEX})\}}", s)
    if "ISTQB" in s:
        sources.append(("ISTQB", "2024"))
    return sources

def categorizeSources(sources: str):
    if sources.startswith(("(implied")):
        return {Rigidity.IMP: getSources(sources)}
    elif "implied" in sources:
        parts = sources.split("implied by")
        parsed = {Rigidity.EXP: getSources(parts[0])}
        # Exclude implicit elements that are also explicit
        parsed[Rigidity.IMP] = [t for t in getSources(parts[1])
                                if t not in parsed[Rigidity.EXP]]
        return parsed
    else:
        return {Rigidity.EXP: getSources(sources)}

# I/O
def readFileAsStr(filename) -> str:
    with open(filename, "r") as file:
        return "\n".join(file.readlines())

def writeFile(lines, filename, helper: bool = False, dir: str = "graphs"):
    lines = [line + '\n' for line in lines]
    filename += ".tex"
    if helper:
        filename = f"build/{filename}"
    else:
        if not filename.startswith(f"assets/{dir}"):
            filename = f"assets/{dir}/{filename}"
        elif filename.startswith(f"assets/graphs/exampleGlossaries"):
            filename = filename.split("/")
            filename.remove("exampleGlossaries")
            filename = "/".join(filename)

    try:
        with open(filename, "r", encoding="utf-8") as readFile:
            existingLines = readFile.readlines()
    except FileNotFoundError:
        existingLines = []

    if existingLines != lines:
        with open(filename, "w+", encoding="utf-8") as outFile:
            outFile.writelines(lines)
    # else:
    #     print(f"No changes to {filename}")