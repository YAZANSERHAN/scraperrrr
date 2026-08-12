"""
Broad hardware / electrical engineering keyword set.
Used as a cheap first-pass filter before the AI relevance check.
Keep this wide -- false positives get filtered out by the AI step,
false negatives never get seen at all, so err on the side of inclusion.
"""

HARDWARE_KEYWORDS = [
    # Core EE / analog
    "analog", "mixed-signal", "mixed signal", "ic design", "circuit design",
    "vlsi", "asic", "soc", "rtl", "verilog", "vhdl", "spice", "spectre",
    "cadence", "synopsys", "layout engineer", "physical design",
    "post-silicon", "post silicon", "dft", "design for test",
    "analog layout", "pll", "adc", "dac", "amplifier", "bandgap",
    "voltage reference", "power management", "pmic",

    # Semiconductor / process
    "semiconductor", "wafer", "fab", "process integration",
    "device physics", "cmos", "finfet", "lithography",

    # Hardware / embedded
    "hardware engineer", "embedded systems", "embedded software",
    "fpga", "pcb design", "pcb layout", "firmware", "signal integrity",
    "power electronics", "rf engineer", "microelectronics",

    # Test / validation
    "test engineer", "validation engineer", "characterization",
    "silicon validation", "bring-up", "bring up",

    # Adjacent
    "electrical engineer", "electronics engineer", "chip design",
    "system on chip", "verification engineer",
]

# Titles/phrases that usually indicate senior roles unsuitable for a
# new-grad / entry-level candidate. Used by the experience filter.
SENIOR_TITLE_MARKERS = [
    "principal", "staff engineer", "director", "vp ", "vice president",
    "head of", "chief", "distinguished engineer", "fellow",
]

# Regex-friendly patterns for "N+ years" experience requirements
YEARS_EXPERIENCE_PATTERN = r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?years?"
MAX_ACCEPTABLE_YEARS = 3  # roles requiring more than this get filtered out
