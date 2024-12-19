import re
    
from helpers import wrapEnv, writeFile

CAT_FOOTNOTE = "\n\t".join([
    "\\footnote{",
    "There may be more than one category given for a single test approach ",
    "\\ifnotpaper (for example, A/B Testing in \\Cref{tab:approachGlossaryExcerpt}) \\fi ",
    "which is indicative of a discrepancy (see \\Cref{multiCats}).} \n"])
toRecord: list[str] = [
    "name", f"category{CAT_FOOTNOTE}(\\Cref{{categories-observ}})",
    "definition", "synonyms (\\Cref{syn-rels})",
    "parents (\\Cref{par-chd-rels})"]

OTHER_NOTES = "other relevant notes"
OTHER_NOTES_EXS = ", ".join(["prerequisites", "uncertainties",
                             "and other sources to investigate"])

methodology_a = """    \\item Identify authoritative sources (\\Cref{sources})
    \\item Identify software testing terminology from each source, focusing
          on test approaches and software qualities
    \\item For each test approach, record its:\n""" + "\n".join([
        f"\t\t  {line}" for line in wrapEnv(
            "enumerate", [f"\t\\item {i[0].upper()}{i[1:]}"
                          for i in toRecord + [OTHER_NOTES +
                                               f" (e.g., {OTHER_NOTES_EXS})"]])])
    
methodology_b = """    \\item Analyze these data for discrepancies
          \\begin{enumerate}
              \\item \\phantomsection{}\\label{manual-discreps}
                    Record discrepancies as they arise during data collection
              \\item Generate relation graphs (\\Cref{\\ifnotpaper graph-gen\\else tools\\fi})
              \\ifnotpaper
              \\item Automatically detect certain classes of discrepancies
                    (\\Cref{auto-discrep-analysis})
              \\item Automatically analyze manually recorded discrepancies from
                    \\labelcref{manual-discreps} (\\Cref{aug-discrep-analysis})
              \\fi
          \\end{enumerate}
    \\item Report results of discrepancy analysis (\\Cref{discreps})
    \\item Seek to resolve these discrepancies (\\Cref{recs})"""
    
# Base methodology overview
writeFile(wrapEnv("enumerate", [methodology_a, methodology_b],
                  arg="ref=Step~\\arabic*"),
          "methodOverview", helper=True)

methodOverviewSem = []
m: str
for i, m in enumerate([methodology_a, methodology_b]):
    old_m = ""
    while old_m != m:
        old_m = m
        # From https://stackoverflow.com/a/640016/10002168
        m = re.sub(r"\s+\([^)]*\)", "", m)
    
    # From https://tex.stackexchange.com/a/1702/192195!
    if not i:
        m += "\n\\setcounter{methodCounter}{\\value{enumi}}"
    else:
        m = "\\setcounter{enumi}{\\value{methodCounter}}\n" + m

    # Hack because enumitem conflicts with beamer :(
    m = "\\framesubtitle{Overview}\n" + wrapEnv(
            "enumerate", re.sub(
                "\\\\labelcref{manual-discreps}",
                "Step~\\\\arabic{enumi}.\\\\ref{manual-discreps}", m)
              #, arg="ref=Step~\\arabic*"
            )
    methodOverviewSem += wrapEnv("frame", [f"\t{line}" for line in m.split("\n")],
                                 param="Methodology") + [""]

# Seminar methodology overview
writeFile(methodOverviewSem, "methodOverviewSem", helper=True)

toRecord[-1] = "and " + toRecord[-1]
methodOverviewIntro = [
    "We start by documenting the \\approachCount{} test approaches mentioned ",
    "by \\srcCount{} sources (described in \\Cref{sources}), recording their ",
    ", ".join([record.replace("(\\Cref", "(see \\Cref") for record in toRecord]),
    f"as applicable. We also record any {OTHER_NOTES}, such as {OTHER_NOTES_EXS}.%"]

# Intro methodology overview
writeFile(methodOverviewIntro, "methodOverviewIntro", helper=True)
