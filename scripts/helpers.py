from enum import Enum, auto
import re
from string import ascii_lowercase
from typing import Optional

# RegEx patterns
AUTHOR_CHARS = r"a-zA-Zßğö.\/_"
AUTHOR_REGEX = fr"(?<!OG )(?!OG )\b(?:van|[A-Z])[{AUTHOR_CHARS} ]+"
YEAR_REGEX = r"\d{4}[a-z]?"
BEGIN_INFO_REGEX = r"(?!al)[a-zA-Z]+\."  # To avoid matching "et al."
NUM_REGEX = r"[A-Zmdclxvi\d\.]+"
NUM_INFO_REGEX = fr"(?:{NUM_REGEX}(?:-|\\=/))*{NUM_REGEX}"
INFO_REGEX = fr"{BEGIN_INFO_REGEX}~{NUM_INFO_REGEX}(?:, (?:{BEGIN_INFO_REGEX}~)?{NUM_INFO_REGEX})*"
PREFIX_REGEX = r"\(|[a-z;] "
# Generated by ChatGPT
SPLIT_REGEX = r',(?!(?:[^()]*\([^()]*\))*[^()]*\)) '

INTERNAL_REFS = {"tab:"}

# Used in multiple files
IMPLICIT_KEYWORDS = ["implied", "inferred", "can be", "should be", "ideally",
                     "usually", "most", "likely", "often", "if", "although"]
warned_multi_unsure = set()
def sortByImplied(ls: list[str]):
    ls = sortIgnoringParens(ls)
    return sorted(ls, key=lambda x: sum(
        # Parenthesis present since explicit relations override implicit ones
        [x.count(f"({imp}") for imp in IMPLICIT_KEYWORDS]) +
        (x.count("?") + 10 if "?" in x else 0))

# Also ignores discrepancy count comments
def sortIgnoringParens(ls):
    return sorted(ls, key=lambda x: re.sub(r"\(.+\) ", "", re.sub(
        r"% Discrep count.+\n\t", "", x)))

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
    if sources.startswith(tuple(f"({imp}" for imp in IMPLICIT_KEYWORDS)):
        return {Rigidity.IMP: getSources(sources)}
    else:
        imps = {imp: sources.find(imp) for imp in IMPLICIT_KEYWORDS
                if sources.find(imp) > 0}
        if imps:
            parts = sources.split(max(imps))
            parsed = {Rigidity.EXP: getSources(parts[0])}
            # Exclude implicit elements that are also explicit
            parsed[Rigidity.IMP] = [t for t in getSources(parts[1])
                                    if t not in parsed[Rigidity.EXP]]
            return parsed

        return {Rigidity.EXP: getSources(sources)}

# Format sources for LaTeX citations
def formatLineWithSources(line, todo=True):
    line = line.replace("(Hamburg and Mogyorodi, 2024)", "\\citepISTQB{}")
    line = line.replace("Hamburg and Mogyorodi, 2024", "\\citealpISTQB{}")

    for swebokAuthor in {"Washizaki", "Bourque and Fairley"}:
        line = line.replace(swebokAuthor, "SWEBOK")
    line = line.replace("ISO/IEC", "ISO_IEC")
    line = line.replace("Mackert GmbH", "SPICE")

    line = re.sub(fr"({NUM_INFO_REGEX})-+({NUM_INFO_REGEX})",
                  r"\1\=/\2", line)
    line = re.sub(fr"({BEGIN_INFO_REGEX}) ({NUM_INFO_REGEX})",
                  r"\1~\2", line)

    if todo:
        # Explicitly *want* to capture "OG"
        line = re.sub(fr"; (OG {AUTHOR_REGEX[15:]}(?:, {YEAR_REGEX}(?:, {INFO_REGEX})?)?)\)",
                    r"\\todo{\1})", line)

    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX}), ({INFO_REGEX}); ({YEAR_REGEX}), ({INFO_REGEX})",
                  r"\\citealp[\3]{\1\2}; \\citeyear[\5]{\1\4}", line)
    line = re.sub(fr"\(({AUTHOR_REGEX}), ({YEAR_REGEX}), ({INFO_REGEX})\)",
                  r"\\citep[\3]{\1\2}", line)
    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX}), ({INFO_REGEX})",
                  r"\\citealp[\3]{\1\2}", line)
    line = re.sub(fr"\(({AUTHOR_REGEX}), ({YEAR_REGEX})\)",
                  r"\\citep{\1\2}", line)
    line = re.sub(fr"({AUTHOR_REGEX}), ({YEAR_REGEX})",
                  r"\\citealp{\1\2}", line)

    line = line.replace(" et al.", "EtAl")
    line = line.replace("van V", "vanV")

    for source in getSources(line):
        line = line.replace(source[0], source[0].replace(" and ", "And"))

    while True:
        newLine = re.sub(fr"\\citeyear(.*){{({AUTHOR_REGEX})({YEAR_REGEX})}}; ({YEAR_REGEX}), ({INFO_REGEX})",
                         r"\\citeyear\1{\2\3}; \\citeyear[\5]{\2\4}", line)
        if newLine == line:
            break
        line = newLine

    line = re.sub(r"\"([\w\s]*)\"", r"``\1''", line)

    return line

def getDiscrepCount(line: list[str], cat, cls, todo=True):
    # The following replacements should only apply when counting discrepancies
    line = line.copy()

    IMP_BY = "implied by"
    # TODO: this should be made more robust as more cases come up
    for i, part in enumerate(line):
        if any(re.search(fr"\b{imp}\b", part) for imp in IMPLICIT_KEYWORDS[1:]):
            line[i] = re.sub(r"if .+ in ", f"{IMP_BY} ", line[i])
            line[i] = re.sub(r"although .+? \((.+?)\)", fr"{IMP_BY} \1", line[i])
            line[i] = re.sub(fr"inferred from.+({AUTHOR_REGEX})", fr"{IMP_BY} \1", line[i])
        for intRef in INTERNAL_REFS:
            line[i] = re.sub(fr"{{{intRef}\w+}}", "", line[i])

    NO_BRACES = {IMP_BY, "ISTQB"}
    sources = [" ".join(
        re.findall(fr'(\{{(?!OG )[^}}]+?\}}|{"|".join([
            f"(?:{noBrace})" for noBrace in NO_BRACES])})',
            formatLineWithSources(term, todo))) for term in line if term]

    if not all(sources):
        return ""
    return f"% Discrep count ({cat}, {cls}): {" | ".join(sources)}\n\t"

# I/O
def readFileAsStr(filename) -> str:
    with open(filename, "r") as file:
        return "\n".join(file.readlines())

def wrapEnv(env: str, lines: list[str] | str,
            param: str = "", arg: str = "") -> list[str]:
    begin = f"\\begin{{{env}}}"
    if param:
        begin += f"{{{param}}}"
    if arg:
        begin += f"[{arg}]"

    end = f"\\end{{{env}}}"

    if isinstance(lines, str):
        return "\n".join([begin, lines, end])
    return [begin, *lines, end]

def writeFile(lines, filename: str, helper: bool = False, dir: str = "graphs"):
    lines = [str(line) + '\n' for line in lines]
    filename += ".tex"
    if helper:
        filename = f"build/{filename}"
    else:
        if not filename.startswith(f"assets/{dir}"):
            filename = f"assets/{dir}/{filename}"
        elif filename.startswith(f"assets/graphs/exampleGlossaries"):
            filename = "/".join(filename.split("/").remove("exampleGlossaries"))

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

def writeLongtblr(filename: str, caption: str, headers: list[str],
                  lines: list[str], widths: list[int] = [],
                  footnotes: list[str] = []):
    # Used for ensuring correct number of xcolumns
    xcolCount = len(headers) - 1
    assert all(line.count("&") == xcolCount for line in lines)
    colSpecList = ["Q[c,m]"]

    # If all given widths are equal, don't change them
    if len(set(widths)) > 1:
        # Include first column
        assert len(widths) == xcolCount
        scale = sum(widths) / len(widths)
        colSpecList += [f"X[{width/scale},m]" for width in widths]
    else:
        colSpecList += ["X[m]"] * xcolCount

    writeFile(["\\begin{longtblr}[",
            *(f"   note{{{x}}} = {{{footnote}}},"
                for x, footnote in zip(ascii_lowercase, footnotes)),
              f"   caption = {{{caption}}},",
              f"   label = {{tab:{filename}}}",
               "   ]{",
              f"   colspec = {{|{"|".join(colSpecList)}|}}, width = \\linewidth,",
            #   f"   colspec = {{|{"|".join(colSpecList)}|}}, width = {width},",
               "   rowhead = 1",
               "   }",
               "  \\hline",
              f"  {" & ".join([f"\\thead{{{h}}}" for h in headers])} \\\\",
               "  \\hline"] + sortByImplied(lines) +
              ["  \\hline", "\\end{longtblr}"],
               filename, True)
