import numpy as np
from pandas import read_csv
import re

# Whether or not to display information for pulling source information
# Will only display information for approaches containing the provided string
DEBUG_SOURCE: str = ""

def debugSource(x, toPrint = ""):
    if isinstance(x, bool):
        if x:
            print(toPrint if toPrint else x)
    elif DEBUG_SOURCE and any(DEBUG_SOURCE in y for y in x):
        print(toPrint if toPrint else x)
        return True
    else:
        return False    

# RegEx patterns
AUTHOR_CHARS = r"a-zA-Zßğö.\/_"
AUTHOR_REGEX = fr"(?<!OG )(?!OG )\b(?:van |[A-Z])[{AUTHOR_CHARS} ]+"
YEAR_REGEX = r"\d{4}[a-z]?"
BEGIN_INFO_REGEX = r"(?!al)[a-zA-Z]+\."  # To avoid matching "et al."
NUM_INFO_REGEX = r"(?:[A-Z\d\.]+, |-)*[A-Z\d\.]+"
PREFIX_REGEX = r"\(|[a-z;] "
# Generated by ChatGPT
SPLIT_REGEX = r',(?!(?:[^()]*\([^()]*\))*[^()]*\)) '

approaches = read_csv('ApproachGlossary.csv')
names = approaches["Name"].to_list()
categories = approaches["Approach Category"].to_list()
synonyms = approaches["Synonym(s)"].to_list()
parents = approaches["Parent(s)"].to_list()

def processCol(col):
    SOURCE_CHUNKS = [AUTHOR_REGEX, YEAR_REGEX, BEGIN_INFO_REGEX]

    # Adds a comma and a space to a RegEx within a non-capturing group
    def cs(regex):
        return fr"(?:{regex}, )"

    def copySources(x):
        # "Pull" sources back (i.e., when a source applies to multiple items)
        for i in range(len(x)-1, 0, -1):
            if (x[i].find("(") > 0 and
                    not re.search(fr"{cs(AUTHOR_REGEX)}|({BEGIN_INFO_REGEX} )", x[i-1])):
                x[i-1] += f" ({x[i].split(" (")[-1]}"
            x[i] = x[i].replace("if they exist", "if it exists")

        # Pre-compile RegEx patterns
        IMPLIED_PATTERNS = [re.compile(fr"({PREFIX_REGEX})({r})")
                            for r in [BEGIN_INFO_REGEX, YEAR_REGEX]]
        HAS_AUTHOR_REGEX = re.compile(cs(AUTHOR_REGEX))

        out = debugSource(x)
        # "Push" sources forward (i.e., when parts of a source are implied)
        while True:
            origX = x.copy()
            for i in range(1, len(x)):
                for j, pattern in enumerate(IMPLIED_PATTERNS):
                    search = pattern.search(x[i])
                    if search:
                        debugSource(out, ["BEGIN", "YEAR"][j])
                        debugSource(out, f"Search: {search.group()} -> {search.groups()}")
                        if (len(search.groups()) == 2 and
                                not HAS_AUTHOR_REGEX.search(x[i].split(search.group())[0])):
                            toPush = re.findall(f"({"?".join(
                                cs(c) for c in SOURCE_CHUNKS[:2-j]
                            )})", x[i-1])
                            debugSource(out, f"regex {f"({"?".join(
                                cs(c) for c in SOURCE_CHUNKS[:2-j]
                            )})"} applied to {x[i-1]}")
                            if toPush:
                                debugSource(out, f"new: {toPush[-1].join(search.groups())}")
                                x[i] = x[i].replace(search.group(),
                                                    toPush[-1].join(search.groups()))
            debugSource(out, x)
            if origX == x:
                return x

    # Handle "Operational (Acceptance) Testing"
    # This ensures "(Acceptance)" appears in the node but doesn't affect processing
    col = [re.split(SPLIT_REGEX, x.replace("(Acceptance) ", ""))
           if isinstance(x, str) else [] for x in col]
    return [copySources(x) for x in col]

names = [n for n in names if isinstance(n, str)]
parents = processCol(parents)
synonyms = processCol(synonyms)

staticApproaches = {
    'ConcreteExecution', 'SymbolicExecution', 'InductiveAssertionMethods',
    'ContentChecking', 'ModelVerification'}
staticKeywords = {'Audit', 'Inspection' 'Proof', 'Review', 'Static', 'Walkthrough'}
dynamicExceptions = {}

categoryDict = {
    "Approach": ([], []),
    "Level": ([], []),
    "Practice": ([], []),
    "Static": ([], []), # Not a category in the same way, but makes for easier code
    "Technique": ([], []),
    "Type": ([], []),
}

UNSURE_KEYWORDS = ["implied", "inferred", "can be", "usually", "most", "often",
                   "if", "although"]
def isUnsure(name):
    return any(unsure in name for unsure in
               {"?", " (Testing)"}.union(f"({term}" for term in UNSURE_KEYWORDS))

def addLineToCategory(key, line):
    if line not in categoryDict[key][1] and "-> ;" not in line:
        categoryDict[key][1].append(line)

def removeInParens(s):
    s = s.replace(" (Testing)", " Testing")
    # s = re.sub(r" \(.*?\) \(.*?\)", "", s)
    # Remove nested parentheses first, if they exist
    s = re.sub(r" \([^\)]*\([^\)]*\)[^\)]*\)", "", s)
    s = re.sub(r"\([^\)]*\([^\)]*\)[^\)]*\)", "", s)
    s = re.sub(r" \(.*?\)", "", s)
    if "(" not in s:
        s = s.strip(")")
    return s.replace("?", "")

def lineBreak(s):
    return f"<{s.replace(" ", "<br/>")}>"

def formatApproach(s):
    s = removeInParens(s)
    for c in "?-/() ":
        s = s.replace(c, "")
    s = s.replace("0", "Zero")
    s = s.replace("1", "One")
    return s.strip(",")

def addNode(name, style = "", key = "Approach"):
    dashed = isUnsure(name)
    if dashed:
        name = name.replace("?", "")
    name = removeInParens(name)

    extras = [f"label={lineBreak(name)}"]
    styles = [s for s in ["dashed" if dashed else "", style] if s]
    if styles:
        extras.append(f'style="{",".join(styles)}"')
    nameLine = f"{formatApproach(name)} [{",".join(extras)}];"

    for k in staticKeywords:
        if k in name and name not in dynamicExceptions:
            categoryDict["Static"][0].append(name)
            staticApproaches.add(formatApproach(name))
            break
    
    if style == "filled" and key == "Static":
        addLineToCategory("Static", nameLine)
        return

    if formatApproach(name) in staticApproaches:
        addLineToCategory("Static", nameLine)
    addLineToCategory(key, nameLine)

for name, category in zip(names, categories):
    if isinstance(category, str):
        for key in categoryDict.keys():
            if key in category or key == "Approach":
                categoryDict[key][0].append(removeInParens(name))
                addNode(name, key=key)

for key in categoryDict.keys():
    categoryDict[key][1].append("")

def addToIterable(s, iterable, key=key):
    if isinstance(iterable, list):
        if removeInParens(s) not in iterable:
            addNode(s, style="dotted", key=key)
            iterable.append(removeInParens(s))
    elif isinstance(iterable, set):
        if formatApproach(s) not in iterable:
            addNode(s, style="filled", key=key)
            iterable.add(formatApproach(s))
    else:
        raise ValueError(f"addToIterable unimplemented for {type(iterable)}")

GREEN = "green"
BLUE = "blue"
MAROON = "maroon"
BLACK = "black"
COLOR_ORDERING = [GREEN, BLUE, MAROON, BLACK]

# Returns a tuple with the color for the rigid relations (if any),
# then for the unsure ones (if any)
def getColor(name):
    def determineColor(s):
        if any(std in s for std in {"IEEE", "ISO", "IEC"}):
            return "green"
        if any(metastd in s for metastd in 
            {"Washizaki", "Bourque and Fairley",
                "Hamburg and Mogyorodi", "Firesmith"}):
            return "blue"
        if any(textbook in s for textbook in
            {"van Vliet", "Patton", "Peters and Pedrycz"}):
            return "maroon"
        return "black"

    if isUnsure(name):
        return (None, determineColor(name))
    else:
        for term in UNSURE_KEYWORDS:
            if term + " " in name:
                name = name.split(term)
                break
        if isinstance(name, list):
            colors = (determineColor(name[0]), determineColor(name[1]))
            if COLOR_ORDERING.index(colors[1]) >= COLOR_ORDERING.index(colors[0]):
                return (determineColor(name[0]), None)
            return colors
        return (determineColor(name), None)

def colorRelations(colors, edge, extra=""):
    out = []
    # Second iteration is for unsure relations
    for i, style in enumerate(['', 'style="dashed"']):
        if colors[i]:
            color = f'color="{colors[i]}"' if colors[i] != BLACK else ""
            out.append(f"{edge}[{",".join(list(filter(None, [extra, style, color])))}];".replace("[]", ""))
    return out

# Add synonym relations
synDict, nameDict = {}, {}
synSets = {}
for name, synonym in zip(names, synonyms):
    rname, fname = removeInParens(name), formatApproach(name)
    for syn in synonym:
        rsyn, fsyn = removeInParens(syn), formatApproach(syn)
        if not (any(minor in syn.lower() for minor in {"spelled", "called"}) or
                fsyn.isupper()):
            nameWithSource = rname + ("?" if name.endswith("?") else "")
            if "(" in syn and syn.count(" (") != rsyn.count(" ("):
                source = syn.split(' (')
                for i in range(source[-1].count(")"), 0, -1):
                    nameWithSource += " (" + source[-i]
            try:
                synDict[rsyn].append(nameWithSource)
            except KeyError:
                synDict[rsyn] = [nameWithSource]
            try:
                nameDict[nameWithSource].append(rsyn)
            except KeyError:
                nameDict[nameWithSource] = [rsyn]
            # To only track relation one way and check inconsistencies
            try:
                if synSets[f"{fname} -> {fsyn}"] != getColor(syn):
                    raise ValueError(
                        f"Mismatch between rigidity of synonyms {fsyn} and {fname}")
            except KeyError:
                synSets[f"{fsyn} -> {fname}"] = getColor(syn)

nameDict.update(synDict)

def formatLineWithSources(line):
    line = line.replace("(Hamburg and Mogyorodi, 2024)", "\\citepISTQB{}")
    line = line.replace("Hamburg and Mogyorodi, 2024", "\\citealpISTQB{}")
    for swebokAuthor in {"Washizaki", "Bourque and Fairley"}:
        line = line.replace(swebokAuthor, "SWEBOK")
    line = line.replace("ISO/IEC", "ISO_IEC")

    # Explicitly *want* to capture "OG"
    line = re.sub(fr"; (OG {AUTHOR_REGEX[15:]}(?:, {YEAR_REGEX}(?:, {BEGIN_INFO_REGEX} {NUM_INFO_REGEX})?)?)\)",
                  r" \\todo{\1})", line)

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

def makeMultiSynLine(syn, terms):
    return formatLineWithSources(
        f"\\item \\textbf{{{syn}:}}\n\t\\begin{{itemize}}\n{'\n'.join(
            f"\t\t\\item {term}" for term in terms)}\n\t\\end{{itemize}}")

expMultiSyns, impMultiSyns = [], []
for key in categoryDict.keys():
    for syn, terms in synDict.items():
        fsyn = formatApproach(syn)
        knownTerm = lambda x: removeInParens(x) in categoryDict[key][0]
        if (knownTerm(syn) or (sum(1 for x in terms if knownTerm(x)) > 1)):
            validTerms = [term for term in terms
                          if (f"{fsyn} -> {formatApproach(term)}" in synSets.keys())
                          and knownTerm(term)]
            if validTerms:
                if key == "Approach" and (len(validTerms) > 1):
                    multiSynsList, synStr = (
                        (impMultiSyns, f"\\emph{{{syn}}}")
                        if not all(synSets[f"{fsyn} -> {formatApproach(term)}"][0]
                                   for term in validTerms) else (expMultiSyns, syn))
                    multiSynsList.append(makeMultiSynLine(synStr, filter(knownTerm, terms)))
                addToIterable(syn, categoryDict[key][0], key)
                for term in validTerms:
                    addToIterable(term, categoryDict[key][0], key)

                    fterm = formatApproach(term)
                    for line in colorRelations(synSets[f"{fsyn} -> {fterm}"],
                                               f"{fterm} -> {fsyn}", "dir=none"):
                        addLineToCategory(key, line)

    if categoryDict[key][1][-1] != "":
        categoryDict[key][1].append("")

    # ONLY USE SAME RANK FOR THESE CATEGORIES
    if key in {}:
        blacklistSyns = set()
        for name, syns in nameDict.items():
            if (len(syns) == 1 and name in categoryDict[key][0] and
                    name not in blacklistSyns and syns[0] in categoryDict[key][0]):
                addLineToCategory(key, f'{{rank=same {formatApproach(
                    name)} {formatApproach(syns[0])}}}')
                print(key, name, syns[0])
                blacklistSyns.update({name, syns[0]})
        if blacklistSyns:
            categoryDict[key][1].append("")

# Sort explicit and implicit synonyms based on number of them with sources
synLines = []
for synList in [expMultiSyns, impMultiSyns]:
    synList.sort(key=lambda x: re.sub(r"\(.+\) ", "", x))
    allSources, someSources, noSources = [], [], []
    for line in synList:
        # The itemized list is itself an item
        if line.count("\\item") - 1 <= line.count("\\cite"):
            allSources.append(line)
        elif line.count("\\cite"):
            someSources.append(line)
        else:
            noSources.append(line)
    synLines += allSources + someSources + noSources

def writeHelperFile(lines, filename):
    lines = "\n".join(lines)

    with open(f"build/{filename}.tex", "w", encoding="utf-8") as outFile:
        outFile.writelines(lines)

writeHelperFile(synLines, "multiSyns")

workingStaticSet = staticApproaches.copy()

# Add parent relations
for name, parent in zip(names, parents):
    # if [x for x in parent + [name] if "keyword" in x.lower()]:
    fname = formatApproach(name)
    for par in parent:
        fpar = formatApproach(par)
        if not fpar:
            continue

        for key in categoryDict.keys():
            for parentLine in colorRelations(
                    getColor(par), f"{fname} -> {fpar}"):
                if key == "Static" and (fname in staticApproaches or
                                        fpar in staticApproaches):
                    addToIterable(name, workingStaticSet, "Static")
                    addToIterable(par, workingStaticSet, "Static")
                    addLineToCategory("Static", parentLine)
                elif (removeInParens(name) in categoryDict[key][0] and
                    removeInParens(par) in categoryDict[key][0]):
                    addLineToCategory(key, parentLine)

def splitListAtEmpty(listToSplit):
    recArr = np.array(listToSplit)
    return [subarray.tolist() for subarray in
            np.split(recArr, np.where(recArr == "")[0]+1)
            if len(subarray) > 0]

def makeParSynLine(chd, par, parSource, synSource):
    return formatLineWithSources(
        f"\\item \\textbf{{``{chd.capitalize()}''}} is called a child of "
        f"\\textbf{{``{par.lower()}''}} in {parSource}, but the two are called "
        f"synonyms in {synSource}.")

parSynLines = set()
parentLines = splitListAtEmpty(categoryDict["Approach"][1])[-1]
for chd, syns in nameDict.items():
    par: str
    for par in syns:
        synLines = [p for p in parentLines if p.startswith(
            f"{formatApproach(chd)} -> {formatApproach(par)}")]
        if synLines:
            if chd in synDict.keys():
                synSource = par.split("(", 1)
                par = removeInParens(par)
            else:
                synSource = chd.split("(", 1)
                chd = removeInParens(chd)

            nameLookup = [name for name in names if name.startswith(chd)]
            if len(set(nameLookup)) != 1:
                raise ValueError(
                    f"Problem with finding child term '{removeInParens(chd)}' in `names`")
            parSource = [parItem for parItem in parents[names.index(nameLookup[0])]
                         if parItem.startswith(par)]
            if len(parSource) != 1:
                raise ValueError(
                    "Problem with finding source for parent relation between"
                     f"'{removeInParens(chd)}' and '{removeInParens(par)}'")
            parSource = parSource[0].split("(", 1)

            if len(synSource) > 1 and len(parSource) > 1:
                parSource = "(" + parSource[-1]
                synSource = "(" + synSource[-1]
                parSynLines.add(makeParSynLine(chd, par, parSource, synSource))

            if isinstance(synSource, str) or isinstance(parSource, str):
                print("Child:", chd, "\nParent:", par)
                if isinstance(synSource, str):
                    print(f"Syn. Source:", synSource)
                else:
                    print(f"Par. Source:", parSource)
                print()

writeHelperFile(sorted(parSynLines, key=lambda x: re.sub(r"\(.+\) ", "", x)),
                "parSyns")

def styleInLine(style, line):
        return re.search(r"label=.+,style=.+" + style, line)

def writeDotFile(lines, filename):
    LONG_EDGE_LABEL = 'label="                "'

    syns = [line.split(" ")[0] for line in lines if styleInLine("dotted", line)]
    synsToRemove = [syn for syn in syns if sum(1 for line in lines if syn in line) < 3]
    lines = [line for line in lines if not any(syn in line for syn in synsToRemove)]

    impTerm, dynTerm = '', ''
    if any(styleInLine("dashed", line) for line in lines):
        impTerm = 'imp5 [label=<Implied<br/>Term> style="dashed"]'

    if any(styleInLine("filled", line) for line in lines):
        dynTerm = 'dyn [label=<Dynamic<br/>Approach> style="filled"]'

    twoSyn = [
        'syn3 [label=<Term>]',
        'syn4 [label=<Synonym<br/>to Both> style="dotted"]',
        'syn5 [label=<Term>]',
        'syn3 -> syn4 -> syn5 [dir=none]',
    ] if len(syns) > len(synsToRemove) else []
    
    def sameRank(lines):
        return ['{', 'rank=same'] + lines + ['}']

    def impOrDynWithSyn(nodes, forceDyn=False):
        if len(nodes) == 1:
            nodes = nodes[0]
        else:
            nodes = f'{{ {" ".join(nodes)} }}'
        return f'{'imp5' if impTerm and not forceDyn else 'dyn'} -> {nodes}'

    def twoSynAlign(nodes):
        synNodes = [f'syn{i}' for i in range(3, 6, 2 if len(nodes) == 2 else 1)]
        for i in range(len(synNodes)):
            synNodes[i] = f'{synNodes[i]} -> {nodes[i]}'
        return synNodes

    extras, align = [], []
    if impTerm and dynTerm:
        extras = sameRank([impTerm, dynTerm])
        align = [impOrDynWithSyn(["imp1", "imp2"]),
                 impOrDynWithSyn(["imp3", "imp4"], forceDyn=True)]
        if twoSyn:
            extras += sameRank(twoSyn)
            align = twoSynAlign(align)
    elif twoSyn:
        align = twoSynAlign([f'imp{i}' for i in range(2, 5)])
        if not (impTerm or dynTerm):
            extras = sameRank(twoSyn)
            align += twoSynAlign([f'imp{i}' for i in range(1, 4)])
        else:
            extras = sameRank([impTerm if impTerm else dynTerm] + twoSyn)
            align = [impOrDynWithSyn(["imp1"])] + align
    elif impTerm or dynTerm:
        extras = [impTerm if impTerm else dynTerm]
        align = [impOrDynWithSyn(["imp2", "imp3"])]

    INDENT = "    "
    extras = [f'{INDENT if line in "}{" else 2*INDENT}{line}' for line in extras]

    # From https://stackoverflow.com/a/65443720/10002168
    legend = [
        '',
        'subgraph cluster_legend {',
        '    label="Legend";',
        # This puts the label at the top, not the bottom, because of the rankdir
        '    labelloc="b";',
        '    fontsize="48pt"',
        '    rankdir=BT',
        '    {',
        '        rank=same',
        '        chd [label="Child"];',
        '        par [label="Parent"];',
        f'        chd -> par [{LONG_EDGE_LABEL}];',
        '        syn1 [label="Synonym"];',
        '        syn2 [label="Synonym"];',
        f'        syn1 -> syn2 [dir=none {LONG_EDGE_LABEL}];',
        '    }',
        '    {',
        '        rank=same',
        '        imp1 [label="Child"];',
        '        imp2 [label=<Implied<br/>Parent>];',
        f'        imp1 -> imp2 [style="dashed" {LONG_EDGE_LABEL}]',
        '        imp3 [label=<Implied<br/>Synonym>];',
        '        imp4 [label=<Implied<br/>Synonym>];',
        f'        imp3 -> imp4 [style="dashed" dir=none {LONG_EDGE_LABEL}]',
        '    }',
    ] + extras + [
        # For alignment
        '    edge [style="invis"]',
        '    imp1 -> chd',
        '    imp2 -> par',
        '    imp3 -> syn1',
        '    imp4 -> syn2',
    ] + align + [
        '}',
        '',
        '// Connect the dummy node to the first node of the legend',
        'start -> chd [style="invis"];',
    ]
    lines = [
        "\\documentclass{article}",
        "\\usepackage{graphicx}",
        "\\usepackage[pdf]{graphviz}",
        "\\usepackage{tikz}",
        "\\usetikzlibrary{arrows,shapes}",
        "",
        "\\begin{document}",
        f"\\digraph{{{filename}}}{{",
        "rankdir=BT;",
        '',
        '// Dummy node to push the legend to the top left',
        'start [style="invis"];',
        "",
    ] + lines + legend + [
        "}",
        "\\end{document}",
    ]

    with open(f"assets/graphs/{filename}.tex", "w") as outFile:
        outFile.writelines(line + '\n' for line in lines)

for key, value in categoryDict.items():
    lines = value[1]
    writeDotFile(lines, f"{key.lower()}Graph")
    unsure = ["dashed"] + [c.split()[0] for c in lines if styleInLine("dashed", c)]
    writeDotFile([c for c in lines if all(x not in c for x in unsure)],
                  f"rigid{key}Graph")

recoveryTerms = ["AvailabilityTesting", "BackupandRecoveryTesting", "BackupRecoveryTesting",
                 "DisasterRecoveryTesting", "FailoverTesting", "FailoverRecoveryTesting",
                 "FailureToleranceTesting", "FaultToleranceTesting", "PerformanceTesting",
                 "PerformancerelatedTesting", "RecoverabilityTesting", "RecoveryTesting",
                 "ReliabilityTesting", "UsabilityTesting"]
# Optimized with ChatGPT to remove redundant checks and extra new lines
recoveryLines = [line for line in categoryDict["Approach"][1]
                 if any(term in line for term in recoveryTerms) or line == ""]

chunks = splitListAtEmpty(categoryDict["Approach"][1])
if len(chunks) == 3:
    nodes = chunks[0] + chunks[1]
    rels = chunks[1] + chunks[2]
elif len(chunks) == 4:
    nodes = chunks[0] + chunks[1]
    rels = chunks[1] + chunks[2] + chunks[3]
else:
    raise ValueError("Unexpected grouping of lines for automatic recovery graph")

rels = [line for line in rels if line == "" or
        (line.split(" -> ")[0] in recoveryTerms and
         line.split(" -> ")[1].split("[")[0].strip(";") in recoveryTerms) or
        (line.split(" ")[1] in recoveryTerms and
         line.split(" ")[2].strip("}") in recoveryTerms)]
nodes = [node for node in nodes if "->" not in node and
         any(node.split(" ")[0] in line for line in rels)]

writeDotFile(nodes+rels, "recoveryGraph")

# print(staticApproaches)