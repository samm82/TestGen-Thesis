from enum import Enum, auto
import re
from typing import Optional

# RegEx patterns
AUTHOR_CHARS = r"a-zA-Zßğö.\/_"
AUTHOR_REGEX = fr"(?<!OG )(?!OG )\b(?:van|[A-Z])[{AUTHOR_CHARS} ]+"
YEAR_REGEX = r"\d{4}[a-z]?"
BEGIN_INFO_REGEX = r"(?!al)[a-zA-Z]+\."  # To avoid matching "et al."
NUM_INFO_REGEX = r"(?:[A-Zmdclxvi\d\.]+(?:, |-))*[A-Zmdclxvi\d\.]+"
PREFIX_REGEX = r"\(|[a-z;] "
# Generated by ChatGPT
SPLIT_REGEX = r',(?!(?:[^()]*\([^()]*\))*[^()]*\)) '

# Used in multiple files
IMPLICIT_KEYWORDS = ["implied", "inferred", "can be", "should be", "ideally",
                     "usually", "most", "likely", "often", "if", "although"]
warned_multi_unsure = set()
def sortByImplied(ls: list[str]):
    return sorted(ls, key=lambda x: sum(
        [x.count(imp) for imp in IMPLICIT_KEYWORDS + ["?"]]))

def sortIgnoringParens(ls):
    return sorted(ls, key=lambda x: re.sub(r"\(.+\) ", "", x))

# only == True returns a string iff the passed `name` is not explicit
def isUnsure(name: str, only: bool = False) -> Optional[str]:
    unsureTerms = {"?", " (Testing)"}.union(f"({term}" for term in IMPLICIT_KEYWORDS)
    if not only:
        unsureTerms.update(f" {term}" for term in IMPLICIT_KEYWORDS)

    outTerms = {unsure for unsure in unsureTerms if unsure in name}
    if (len(outTerms) > 1 and "?" not in outTerms and
            name not in warned_multi_unsure):
        print(f"Multiple 'unsure' cutoffs in {name}.")
        warned_multi_unsure.add(name)

    return (sorted(outTerms, key=name.index, reverse=True)[0]
            if outTerms else None)

class Rigidity(Enum):
    EXP = auto()
    IMP = auto()

    # Sources for discrepancies

def getSources(s) -> list[tuple[str, str]]:
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

    # Sources for citations

def formatLineWithSources(line, todo=True):
    line = line.replace("(Hamburg and Mogyorodi, 2024)", "\\citepISTQB{}")
    line = line.replace("Hamburg and Mogyorodi, 2024", "\\citealpISTQB{}")

    for swebokAuthor in {"Washizaki", "Bourque and Fairley"}:
        line = line.replace(swebokAuthor, "SWEBOK")
    line = line.replace("ISO/IEC", "ISO_IEC")
    line = line.replace("Mackert GmbH", "SPICE")

    if todo:
        # Explicitly *want* to capture "OG"
        line = re.sub(fr"; (OG {AUTHOR_REGEX[15:]}(?:, {YEAR_REGEX}(?:, {BEGIN_INFO_REGEX} {NUM_INFO_REGEX})?)?)\)",
                    r"\\todo{\1})", line)

    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX}), ({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX}); ({YEAR_REGEX}), ({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX})",
                  r"\\citealp[\3~\4]{\1\2}; \\citeyear[\6~\7]{\1\5}", line)
    line = re.sub(fr"\(({AUTHOR_REGEX}), ({YEAR_REGEX}), ({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX})\)",
                  r"\\citep[\3~\4]{\1\2}", line)
    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX}), ({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX})",
                  r"\\citealp[\3~\4]{\1\2}", line)
    line = re.sub(fr"\(({AUTHOR_REGEX}), ({YEAR_REGEX})\)",
                  r"\\citep{\1\2}", line)
    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX})",
                  r"\\citealp{\1\2}", line)

    line = line.replace(" et al.", "EtAl")
    line = line.replace("van V", "vanV")

    for source in getSources(line):
        line = line.replace(source[0], source[0].replace(" and ", "And"))

    # if "17, 25" in line: input(line)

    line = re.sub(fr"\[([\w\d~.]+)\]{{(\w+)}}, ({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX})",
                  r"[\1,~\3~\4]{\2}", line)

    while True:
        newLine = re.sub(fr"({BEGIN_INFO_REGEX}(?:~[\d\.]+-?,)*) ({NUM_INFO_REGEX})",
                                r"\1~\2", line)
        if newLine == line:
            break
        line = newLine

    line = re.sub(r"\"([\w\s]*)\"", r"``\1''", line)

    return line

def getDiscrepCount(line, cat, cls, todo=True, newlineAfter=True):
    # TODO: "implied by" isn't stable
    NO_BRACES = {"implied by", "ISTQB"}
    sources = " | ".join(" ".join(
                re.findall(fr'(\{{(?!OG )[^}}]+?\}}|{"|".join([
                    f"(?:{noBrace})" for noBrace in NO_BRACES])})',
                    formatLineWithSources(term, todo)))
                for term in line if term)
    if sources:
        discrepCount = f"% Discrep count ({cat}, {cls}): {sources}"
        return f"{discrepCount}\n" if newlineAfter else f"\n{discrepCount}"
    return ""

# I/O
def readFileAsStr(filename) -> str:
    with open(filename, "r") as file:
        return "\n".join(file.readlines())

def writeFile(lines, filename, helper: bool = False, dir: str = "graphs"):
    lines = [str(line) + '\n' for line in lines]
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