"""MACCS key definitions and SMARTS patterns.

The 166 MACCS structural keys as defined in the MDL MACCS keys.
Keys 1-166 are the public keys (key 0 is not used).
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class MACCSKeyDefinition:
    """Definition of a single MACCS key."""

    key_number: int
    smarts: str
    description: str
    category: str


# MACCS Keys SMARTS patterns and descriptions
# Based on RDKit's MACCSkeys implementation
MACCS_DEFINITIONS: dict[int, MACCSKeyDefinition] = {
    1: MACCSKeyDefinition(1, "?", "ISOTOPE (not implemented)", "special"),
    2: MACCSKeyDefinition(2, "[#103]", "Atomic num >103", "element"),
    3: MACCSKeyDefinition(3, "[#102]", "Group IVb, Vb, VIb Rows 4-6", "element"),
    4: MACCSKeyDefinition(4, "[#101]", "Actinide", "element"),
    5: MACCSKeyDefinition(5, "[#100]", "Group IIIB, IVB (Sc, Ti, Y, Zr, Hf)", "element"),
    6: MACCSKeyDefinition(6, "[#99]", "Lanthanide", "element"),
    7: MACCSKeyDefinition(7, "[#98]", "Group VB, VIB, VIIB (V, Cr, Mn, Nb, Mo, Tc, Ta, W, Re)", "element"),
    8: MACCSKeyDefinition(8, "[#97]", "Group VIIIB (Fe, Co, Ni, Ru, Rh, Pd, Os, Ir, Pt)", "element"),
    9: MACCSKeyDefinition(9, "[#96]", "Group IB, IIB (Cu, Zn, Ag, Cd, Au, Hg)", "element"),
    10: MACCSKeyDefinition(10, "[#95]", "Group IIIa (B, Al, Ga, In, Tl)", "element"),
    11: MACCSKeyDefinition(11, "[Ge,Sn,Pb]", "Group IVa (Ge, Sn, Pb)", "element"),
    12: MACCSKeyDefinition(12, "[As,Sb,Bi]", "Group Va (As, Sb, Bi)", "element"),
    13: MACCSKeyDefinition(13, "[Se,Te,Po]", "Group VIa (Se, Te, Po)", "element"),
    14: MACCSKeyDefinition(14, "[#9,#17,#35,#53,#85]", "Halogen (F, Cl, Br, I, At)", "element"),
    15: MACCSKeyDefinition(15, "[B,Si,P,S]", "B, Si, P, S", "element"),
    16: MACCSKeyDefinition(16, "[Li,Na,K,Rb,Cs,Fr,Be,Mg,Ca,Sr,Ba,Ra]", "Alkali/Alkaline metals", "element"),
    17: MACCSKeyDefinition(17, "[#6]~[#6]~[#6]~[#6]~[#6]~[#6]~[#6]~[#6]", "4 or more C atoms", "topology"),
    18: MACCSKeyDefinition(18, "[#6]~[#6]~[#6]~[#6]~[#6]~[#6]", "4 or more C atoms", "topology"),
    19: MACCSKeyDefinition(19, "[#7]~[#6]~[#8]~[#6]", "N-C-O-C", "functional"),
    20: MACCSKeyDefinition(20, "[#16]-[#16]", "S-S", "functional"),
    21: MACCSKeyDefinition(21, "[#8]~[#6]~[#8]~[#6]~[#8]", "O-C-O-C-O", "functional"),
    22: MACCSKeyDefinition(22, "[!#6;!#1]~1~*~*~*~1", "Heterocycle with 4 atoms", "ring"),
    23: MACCSKeyDefinition(23, "[#16]~[#6]~[#7]", "S-C-N", "functional"),
    24: MACCSKeyDefinition(24, "[#7]~[#6]~[#7]~[#6]~[#7]", "N-C-N-C-N", "functional"),
    25: MACCSKeyDefinition(25, "[#8]~[#16]~[#8]", "O-S-O", "functional"),
    26: MACCSKeyDefinition(26, "[#7]#[#6]~[#6]", "N#C-C", "functional"),
    27: MACCSKeyDefinition(27, "[!#6;!#1]~1~*~*~1", "3-membered heterocycle", "ring"),
    28: MACCSKeyDefinition(28, "[#7]~[#6](~[#8])~[#8]", "N-C(=O)-O", "functional"),
    29: MACCSKeyDefinition(29, "[#7]-[#8]", "N-O", "functional"),
    30: MACCSKeyDefinition(30, "[#7]~[#6](~[#7])~[#7]", "NC(N)N", "functional"),
    31: MACCSKeyDefinition(31, "[#6]=,:[#6]~[#6]=,:[#6]", "C=C-C=C", "functional"),
    32: MACCSKeyDefinition(32, "[!#6;!#1]~[CH2]~[!#6;!#1]", "QACH2AQ", "functional"),
    33: MACCSKeyDefinition(33, "[#16]=,:[#6]", "S=C", "functional"),
    34: MACCSKeyDefinition(34, "[CH3]~[!#6;!#1]", "CH3-Q (Q=heteroatom)", "functional"),
    35: MACCSKeyDefinition(35, "[!#6;!#1]~[#7]", "Q-N", "functional"),
    36: MACCSKeyDefinition(36, "[#16]~[#8]", "S-O", "functional"),
    37: MACCSKeyDefinition(37, "[#16;!H0]", "S with H", "functional"),
    38: MACCSKeyDefinition(38, "[#7]~[#7]~[#6](~[#6])~[#6]", "NNC(C)C", "functional"),
    39: MACCSKeyDefinition(39, "[!#6;!#1]~1~*~*~*~*~*~1", "6-membered heterocycle", "ring"),
    40: MACCSKeyDefinition(40, "[#8]=,:[#6]~[#8]=,:[#6]", "O=C-O-C=O", "functional"),
    41: MACCSKeyDefinition(41, "[!#6;!#1;!H0]~*~[!#6;!#1;!H0]", "QH-A-QH", "functional"),
    42: MACCSKeyDefinition(42, "[!#6;!#1]~1~*~*~*~1", "4-membered heterocycle", "ring"),
    43: MACCSKeyDefinition(43, "[#6H3]", "CH3", "functional"),
    44: MACCSKeyDefinition(44, "[#7]~*~[#7;H1]", "N-A-NH", "functional"),
    45: MACCSKeyDefinition(45, "[#7]~*~*~[#8]", "N-A-A-O", "functional"),
    46: MACCSKeyDefinition(46, "[#7]~*~*~[#7]", "N-A-A-N", "functional"),
    47: MACCSKeyDefinition(47, "[#7]~*~*~*~[#8]", "N-A-A-A-O", "functional"),
    48: MACCSKeyDefinition(48, "[!#6;!#1]~1~*~*~*~*~1", "5-membered heterocycle", "ring"),
    49: MACCSKeyDefinition(49, "[!#6;!#1]~[!#6;!#1]", "Q-Q", "functional"),
    50: MACCSKeyDefinition(50, "[#16]-[#6]-[#6]-[#6]", "S-C-C-C", "functional"),
    51: MACCSKeyDefinition(51, "[#8]-[#6]-[#6]-[#7]", "O-C-C-N", "functional"),
    52: MACCSKeyDefinition(52, "[#8]-[#6]-[#6]=,:[#8]", "O-C-C=O", "functional"),
    53: MACCSKeyDefinition(53, "[!#6;!#1]~[CH3]", "Q-CH3", "functional"),
    54: MACCSKeyDefinition(54, "[!#6;!#1]~[#7]", "Q-N", "functional"),
    55: MACCSKeyDefinition(55, "[#7]~[#8]", "N-O", "functional"),
    56: MACCSKeyDefinition(56, "[#8]~[#6](~[#7])~[#6]", "O-C(N)-C", "functional"),
    57: MACCSKeyDefinition(57, "[!#6;!#1]~[#16]", "Q-S", "functional"),
    58: MACCSKeyDefinition(58, "[#16]~[#7]", "S-N", "functional"),
    59: MACCSKeyDefinition(59, "[#16]~[#6]~[#7]", "S-C-N", "functional"),
    60: MACCSKeyDefinition(60, "[#16]~[#6]~[#8]", "S-C-O", "functional"),
    61: MACCSKeyDefinition(61, "[#8]=,:[#6]~[#6]=,:[#6]", "O=C-C=C", "functional"),
    62: MACCSKeyDefinition(62, "[#7]~[#6]~[#6]=,:[#6]", "N-C-C=C", "functional"),
    63: MACCSKeyDefinition(63, "[#7]=,:[#6]~[#7]", "N=C-N", "functional"),
    64: MACCSKeyDefinition(64, "[#7]~[#6]~[#6]:,=[#6]", "N-C-C=C", "functional"),
    65: MACCSKeyDefinition(65, "[!#6;!#1]~[#6](~[!#6;!#1])~[!#6;!#1]", "QC(Q)Q", "functional"),
    66: MACCSKeyDefinition(66, "[#6]-[#6](=[#8])-[#6]", "C-C(=O)-C", "functional"),
    67: MACCSKeyDefinition(67, "[#8]=,:[#16]", "O=S", "functional"),
    68: MACCSKeyDefinition(68, "[#16]~[#6]~[#16]", "S-C-S", "functional"),
    69: MACCSKeyDefinition(69, "[#6]-[#16]-[#6]", "C-S-C", "functional"),
    70: MACCSKeyDefinition(70, "[#8]~[#16](~[#8])~[#8]", "O-S(O)-O", "functional"),
    71: MACCSKeyDefinition(71, "[#16]-[#8]", "S-O", "functional"),
    72: MACCSKeyDefinition(72, "[#6]#[#7]", "C#N", "functional"),
    73: MACCSKeyDefinition(73, "[#9]", "Fluorine", "element"),
    74: MACCSKeyDefinition(74, "[!#6;!#1;!H0]~*~[!#6;!#1;!H0]", "QH-A-QH", "functional"),
    75: MACCSKeyDefinition(75, "[#8]=,:[#6]~[#7]~[#6]", "O=C-N-C", "functional"),
    76: MACCSKeyDefinition(76, "[#17]", "Chlorine", "element"),
    77: MACCSKeyDefinition(77, "[#35]", "Bromine", "element"),
    78: MACCSKeyDefinition(78, "[#53]", "Iodine", "element"),
    79: MACCSKeyDefinition(79, "[#7;!H0]", "N with hydrogen", "functional"),
    80: MACCSKeyDefinition(80, "[#8]~[#6](~[#6])~[#6]", "O-C(C)-C", "functional"),
    81: MACCSKeyDefinition(81, "[!#6;!#1]~[CH2]~[#6]", "Q-CH2-C", "functional"),
    82: MACCSKeyDefinition(82, "[#7]~*~*~*~[#7]", "N-A-A-A-N", "functional"),
    83: MACCSKeyDefinition(83, "[!#6;!#1]~[CH2]~[!#6;!#1]", "Q-CH2-Q", "functional"),
    84: MACCSKeyDefinition(84, "[#6]=,:[#7]", "C=N", "functional"),
    85: MACCSKeyDefinition(85, "[#7]~*~[#8]", "N-A-O", "functional"),
    86: MACCSKeyDefinition(86, "[!#6;!#1]~[#7]~[#6]", "Q-N-C", "functional"),
    87: MACCSKeyDefinition(87, "[#7]~[#6](~[#8])~[#6]", "N-C(=O)-C", "functional"),
    88: MACCSKeyDefinition(88, "[!#6;!#1]~[!#6;!#1]", "Q-Q", "functional"),
    89: MACCSKeyDefinition(89, "[#8]-[#6]=[#8]", "O-C=O", "functional"),
    90: MACCSKeyDefinition(90, "[#6]=[#7]", "C=N", "functional"),
    91: MACCSKeyDefinition(91, "[#7]~[#6](~[#7])~[#6]", "N-C(N)-C", "functional"),
    92: MACCSKeyDefinition(92, "[#6]~[#8]~[#6]", "C-O-C", "functional"),
    93: MACCSKeyDefinition(93, "[#6]~[#7]~[#6]", "C-N-C", "functional"),
    94: MACCSKeyDefinition(94, "[#8]~[#6]~[#8]", "O-C-O", "functional"),
    95: MACCSKeyDefinition(95, "[#7]~[#6]~[#7]", "N-C-N", "functional"),
    96: MACCSKeyDefinition(96, "[#7]~[#8]", "N-O", "functional"),
    97: MACCSKeyDefinition(97, "[#8]-[#6]-[#6]-[#8]", "O-C-C-O", "functional"),
    98: MACCSKeyDefinition(98, "[!#6;!#1]~*~[CH2]~*", "QA(A)A", "functional"),
    99: MACCSKeyDefinition(99, "[#6]=,:[#6]", "C=C", "functional"),
    100: MACCSKeyDefinition(100, "[#7]~[CH2]~[#6]", "N-CH2-C", "functional"),
    101: MACCSKeyDefinition(101, "[#6]~[#16]~[#6]", "C-S-C", "functional"),
    102: MACCSKeyDefinition(102, "[#7]~*~[#6]=,:[#8]", "N-A-C=O", "functional"),
    103: MACCSKeyDefinition(103, "[#7]~*~*~[#6]=,:[#8]", "N-A-A-C=O", "functional"),
    104: MACCSKeyDefinition(104, "[#7]~*~*~*~[#6]=,:[#8]", "N-A-A-A-C=O", "functional"),
    105: MACCSKeyDefinition(105, "[#7]~*~*~*~*~[#6]=,:[#8]", "N-A-A-A-A-C=O", "functional"),
    106: MACCSKeyDefinition(106, "[#7]~1~*~*~[#8]~*~1", "N in 5-ring with O", "ring"),
    107: MACCSKeyDefinition(107, "[!#6;!#1]~1~*~*~*~*~*~*~1", "7-membered heterocycle", "ring"),
    108: MACCSKeyDefinition(108, "[#6]=[#6]~[#7]", "C=C-N", "functional"),
    109: MACCSKeyDefinition(109, "[#53]", "Iodine", "element"),
    110: MACCSKeyDefinition(110, "[!#6;!#1]~1~*~*~*~1", "4-membered heterocycle", "ring"),
    111: MACCSKeyDefinition(111, "[#6;H3,H4]", "CH4 or CH3", "functional"),
    112: MACCSKeyDefinition(112, "[#8]-*-*-[#7]", "O-A-A-N", "functional"),
    113: MACCSKeyDefinition(113, "[#16]-*-*-[#7]", "S-A-A-N", "functional"),
    114: MACCSKeyDefinition(114, "[#16]=,:[#6]-[#7]", "S=C-N", "functional"),
    115: MACCSKeyDefinition(115, "[#16]-*-*-[#8]", "S-A-A-O", "functional"),
    116: MACCSKeyDefinition(116, "[#8]=,:[#6]-[#6]=,:[#8]", "O=C-C=O", "functional"),
    117: MACCSKeyDefinition(117, "[#6]-[#6](=[#8])-[#8]-[#6]", "C-C(=O)O-C (ester)", "functional"),
    118: MACCSKeyDefinition(118, "[!#6;!#1]~1~*~*~*~*~*~1", "6-membered heterocycle", "ring"),
    119: MACCSKeyDefinition(119, "[#7]-[!#6;!#1;!H0]", "N-QH", "functional"),
    120: MACCSKeyDefinition(120, "[#8]-*-[#6]=,:[#8]", "O-A-C=O", "functional"),
    121: MACCSKeyDefinition(121, "[!#6;!#1]~[#6](~[!#6;!#1])~[!#6;!#1]", "QC(Q)Q", "functional"),
    122: MACCSKeyDefinition(122, "[#6]-[#6](=[#8])-[#7]", "C-C(=O)-N (amide)", "functional"),
    123: MACCSKeyDefinition(123, "[#8]-*-[#8]", "O-A-O", "functional"),
    124: MACCSKeyDefinition(124, "[#6](~[#8])(~[#8])", "C with 2 oxygens", "functional"),
    125: MACCSKeyDefinition(125, "[#6](~[#6])(~[#6])(~[#6])(~[!#6;!#1])", "C(C)(C)(C)Q", "functional"),
    126: MACCSKeyDefinition(126, "[#8]!:*:*", "O not in ring connected to ring", "topology"),
    127: MACCSKeyDefinition(127, "[#6]=[#6]~[#6]=[#6]", "C=C-C=C", "functional"),
    128: MACCSKeyDefinition(128, "[#6]=[#6]~[#8]", "C=C-O", "functional"),
    129: MACCSKeyDefinition(129, "[!#6;!#1]~[#6]~[#7]~[#6]", "Q-C-N-C", "functional"),
    130: MACCSKeyDefinition(130, "[#7]-*-[#8]", "N-A-O", "functional"),
    131: MACCSKeyDefinition(131, "[!#6;!#1]~*~*~[#6;H1,H0;!$([#6](-*)(-*)(-*)-*)]", "Q-A-A-CH or C", "functional"),
    132: MACCSKeyDefinition(132, "[#6;H3,H4]", "CH4 or CH3", "functional"),
    133: MACCSKeyDefinition(133, "[#7]!:*:*", "N not in ring connected to ring", "topology"),
    134: MACCSKeyDefinition(134, "[#8]=,:[#6]-[#8]-[#6]", "O=C-O-C", "functional"),
    135: MACCSKeyDefinition(135, "[!#6;!#1]~[CH3]", "Q-CH3", "functional"),
    136: MACCSKeyDefinition(136, "[!#6;!#1]~[#7]", "Q-N", "functional"),
    137: MACCSKeyDefinition(137, "[#7]-[#8]", "N-O", "functional"),
    138: MACCSKeyDefinition(138, "[#8]=,:[#6]-[#7]-[#6]", "O=C-N-C", "functional"),
    139: MACCSKeyDefinition(139, "[!#6;!#1]~[#16]", "Q-S", "functional"),
    140: MACCSKeyDefinition(140, "[!#6;!#1]~*~*~[#7]", "Q-A-A-N", "functional"),
    141: MACCSKeyDefinition(141, "[#8]=,:[#6]-[#8]", "O=C-O (carboxylic acid/ester)", "functional"),
    142: MACCSKeyDefinition(142, "[#6]-[#6]-[#6]#[#6]", "C-C-C#C", "functional"),
    143: MACCSKeyDefinition(143, "[!#6;!#1]~[CH2]~[!#6;!#1]", "Q-CH2-Q", "functional"),
    144: MACCSKeyDefinition(144, "[#16]=,:[!#6;!#1]", "S=Q", "functional"),
    145: MACCSKeyDefinition(145, "[#6]#[#6]~[#6]", "C#C-C", "functional"),
    146: MACCSKeyDefinition(146, "[#6]!@[#6]!@[#6]", "C!@C!@C (3 non-ring bonded C)", "topology"),
    147: MACCSKeyDefinition(147, "[!#6;!#1;!H0]", "Q with H", "functional"),
    148: MACCSKeyDefinition(148, "[#7]~[#6]~[#8]", "N-C-O", "functional"),
    149: MACCSKeyDefinition(149, "[#7]=,:[#6]~[#6]", "N=C-C", "functional"),
    150: MACCSKeyDefinition(150, "[#6]~[#7]~[#8]", "C-N-O", "functional"),
    151: MACCSKeyDefinition(151, "[#7]~*~[#6]", "N-A-C", "functional"),
    152: MACCSKeyDefinition(152, "[#6]:[#6]", "C:C (aromatic)", "aromatic"),
    153: MACCSKeyDefinition(153, "[#8]!:*:*", "O not in ring connected to ring", "topology"),
    154: MACCSKeyDefinition(154, "[#6]=,:[#8]", "C=O (carbonyl)", "functional"),
    155: MACCSKeyDefinition(155, "[#7]!:*:*", "N not in ring connected to ring", "topology"),
    156: MACCSKeyDefinition(156, "[#6]-[#8]", "C-O", "functional"),
    157: MACCSKeyDefinition(157, "[#6]-[#7]", "C-N", "functional"),
    158: MACCSKeyDefinition(158, "[#6]-[#7]", "C-N bond", "functional"),
    159: MACCSKeyDefinition(159, "[#8]", "Oxygen (≥1)", "element"),
    160: MACCSKeyDefinition(160, "[C;H3,H4]", "CH3 or methane", "functional"),
    161: MACCSKeyDefinition(161, "[#7]", "Nitrogen", "element"),
    162: MACCSKeyDefinition(162, "a", "Aromatic atom", "aromatic"),
    163: MACCSKeyDefinition(163, "*~1~*~*~*~*~*~1", "6-membered ring", "ring"),
    164: MACCSKeyDefinition(164, "[#8]", "Oxygen", "element"),
    165: MACCSKeyDefinition(165, "[R]", "Ring atom (any ring)", "ring"),
    166: MACCSKeyDefinition(166, "?", "Undefined / not implemented", "special"),
}


class MACCSKeys:
    """MACCS key definitions and lookup."""

    @staticmethod
    def get_key(key_number: int) -> Optional[MACCSKeyDefinition]:
        """Get definition for a specific MACCS key."""
        return MACCS_DEFINITIONS.get(key_number)

    @staticmethod
    def get_smarts(key_number: int) -> Optional[str]:
        """Get SMARTS pattern for a specific MACCS key."""
        key = MACCS_DEFINITIONS.get(key_number)
        return key.smarts if key else None

    @staticmethod
    def get_description(key_number: int) -> Optional[str]:
        """Get description for a specific MACCS key."""
        key = MACCS_DEFINITIONS.get(key_number)
        return key.description if key else None

    @staticmethod
    def get_category(key_number: int) -> Optional[str]:
        """Get category for a specific MACCS key."""
        key = MACCS_DEFINITIONS.get(key_number)
        return key.category if key else None

    @staticmethod
    def get_all_keys() -> dict[int, MACCSKeyDefinition]:
        """Get all MACCS key definitions."""
        return MACCS_DEFINITIONS.copy()

    @staticmethod
    def get_keys_by_category(category: str) -> dict[int, MACCSKeyDefinition]:
        """Get all MACCS keys in a specific category."""
        return {
            k: v for k, v in MACCS_DEFINITIONS.items() if v.category == category
        }

    # DEAD CODE — flagged for removal
    # @staticmethod
    # def get_categories() -> list[str]:
    #     """Get all unique categories."""
    #     return list(set(v.category for v in MACCS_DEFINITIONS.values()))

    @staticmethod
    def search_keys(query: str) -> dict[int, MACCSKeyDefinition]:
        """Search MACCS keys by description or SMARTS."""
        query = query.lower()
        return {
            k: v
            for k, v in MACCS_DEFINITIONS.items()
            if query in v.description.lower() or query in v.smarts.lower()
        }

    @staticmethod
    def is_valid_key(key_number: int) -> bool:
        """Check if a key number is valid."""
        return key_number in MACCS_DEFINITIONS
