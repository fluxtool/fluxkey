
import secrets
import string
import random

# Common word list for keyphrase generation
_WORDS = [
    "cloud","storm","frost","flame","blade","stone","river","shadow","crystal","nexus",
    "forge","prime","delta","vector","cipher","pulse","nova","apex","zenith","core",
    "steel","vortex","echo","signal","orbit","phase","relay","axis","surge","drift",
    "lunar","solar","comet","nebula","quasar","fusion","matrix","logic","spark","flux",
    "pixel","byte","node","stack","cache","token","chain","vault","shield","ghost",
    "titan","crown","dragon","falcon","raven","wolf","lion","viper","hawk","cobra",
    "thunder","breach","strike","impact","power","force","hyper","ultra","mega","turbo",

    # ── TECH / CYBER ──
    "kernel","binary","quantum","neural","cyber","protocol","packet","server","client","router",
    "encrypt","decrypt","hash","salt","entropy","firewall","sandbox","daemon","thread","process",
    "runtime","compile","script","execute","terminal","console","debug","inject","exploit","payload",
    "override","system","root","admin","access","control","gateway","bridge","link","port",

    # ── SCI-FI / SPACE ──
    "galaxy","cosmos","asteroid","eclipse","supernova","gravity","singularity","wormhole","orbitals",
    "starlight","void","plasma","radiant","stellar","ion","magnet","pulsewave","darkmatter","antimatter",
    "orbitron","celestial","astral","cometary","lumin","photon","spectrum","flare","novae","rings",

    # ── ELEMENTAL ──
    "ember","blaze","inferno","glacier","icefall","tidal","tsunami","current","tempest","cyclone",
    "whirlwind","dust","sandstorm","quake","shockwave","sparkle","emberfall","frostbite","icicle","mist",
    "steam","pressure","eruption","lava","molten","crackle","flash","stormfront","overcharge","surgeflow",

    # ── FANTASY ──
    "arcane","rune","glyph","spell","enchant","sorcery","alchemy","wizard","mage","warlock",
    "paladin","knight","assassin","rogue","hunter","warden","guardian","sentinel","oracle","seer",
    "relic","artifact","totem","amulet","sigil","curse","blessing","mythic","legend","epic",

    # ── ANIMALS / BEASTS ──
    "panther","tiger","eagle","griffin","phoenix","hydra","serpent","minotaur","kraken","leviathan",
    "scorpion","jaguar","lynx","fox","badger","stallion","rhino","bull","beast","predator",

    # ── POWER / STATUS ──
    "dominion","empire","king","queen","overlord","champion","elite","master","supreme","alpha",
    "omega","primecore","ultramax","godmode","limitless","infinite","unstoppable","invincible",
    "absolute","peak","final","ultimate","ascension","transcend","evolve","awaken","empower","enhance",

    # ── ABSTRACT / STYLE ──
    "voided","shaded","silent","hidden","masked","veiled","broken","fractured","shattered","glitched",
    "warped","twisted","distorted","shifted","fragment","pulsecore","darkcore","lightcore","softcore",
    "hardcore","deep","voidborn","stormborn","fireborn","iceborn","starborn","codeborn","nether",

    # ── EXTRA COOL WORDS ──
    "velocity","momentum","vectorial","dynamics","overdrive","afterburn","hyperspeed","quickshift",
    "snap","burst","charge","dash","blink","warp","teleport","jump","slide","glide","rush","boost",
    "grid","frame","layer","render","shader","texture","engine","module","systemx","corex"
]

_AMBIGUOUS = set("0Ol1I|lB8S5Z2")

class PasswordGenerator:

    def generate(self, length=20, upper=True, numbers=True, symbols=True,
                 no_ambiguous=False, no_repeats=False):
        """Generate a cryptographically secure random password."""
        chars = string.ascii_lowercase
        if upper:   chars += string.ascii_uppercase
        if numbers: chars += string.digits
        if symbols: chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"

        if no_ambiguous:
            chars = "".join(c for c in chars if c not in _AMBIGUOUS)

        if not chars:
            chars = string.ascii_lowercase

        # Guarantee at least one from each enabled set
        pwd = []
        if upper and not no_ambiguous:
            pwd.append(secrets.choice(string.ascii_uppercase))
        elif upper:
            pool = [c for c in string.ascii_uppercase if c not in _AMBIGUOUS]
            if pool: pwd.append(secrets.choice(pool))
        if numbers and not no_ambiguous:
            pwd.append(secrets.choice(string.digits))
        elif numbers:
            pool = [c for c in string.digits if c not in _AMBIGUOUS]
            if pool: pwd.append(secrets.choice(pool))
        if symbols:
            pwd.append(secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"))

        char_list = list(chars)
        if no_repeats:
            # Generate without repetition
            char_list = list(set(chars))
            random.shuffle(char_list)
            remaining = [c for c in char_list if c not in pwd]
            need = length - len(pwd)
            if need > len(remaining):
                # Fall back to allowing repeats if pool too small
                while len(pwd) < length:
                    pwd.append(secrets.choice(chars))
            else:
                pwd += remaining[:need]
        else:
            while len(pwd) < length:
                pwd.append(secrets.choice(chars))

        random.shuffle(pwd)
        return "".join(pwd[:length])

    def generate_keyphrase(self, length=20):
        """
        Generate a memorable keyphrase: WordWordNumber!
        Length controls approximate total character count.
        Combines 2-4 words + numbers + separator to hit target length.
        """
        phrase_parts = []
        total = 0
        while total < length - 4:
            word = secrets.choice(_WORDS)
            phrase_parts.append(word.capitalize())
            total += len(word)

        # Add number suffix
        num = secrets.randbelow(9000) + 100
        phrase_parts.append(str(num))

        # Add symbol
        phrase_parts.append(secrets.choice("!@#$&*?"))

        result = "".join(phrase_parts)
        # Trim or pad to approximate length
        if len(result) > length:
            result = result[:length]
        return result

    def estimate_entropy(self, password: str) -> float:
        """Calculate Shannon entropy estimate in bits."""
        import math
        pool = 0
        if any(c.islower() for c in password): pool += 26
        if any(c.isupper() for c in password): pool += 26
        if any(c.isdigit() for c in password): pool += 10
        if any(not c.isalnum() for c in password): pool += 32
        if pool == 0: return 0.0
        return len(password) * math.log2(pool)
