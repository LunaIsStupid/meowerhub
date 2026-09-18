from timelength import TimeLength, FailureFlags

def extract(string: str) -> tuple[int, str, str]:
    words = string.split()
    used = 0
    seconds = 0
    check = []

    for word in words:
        check.append(word)
        tl = TimeLength(" ".join(check))
        if not tl.result.invalid:
            new = int(tl.result.seconds)
            if new == seconds or (len(check) == 1 and word.replace(".", "").isdigit()): continue
            used, seconds = len(check), new
        elif any(t != FailureFlags.LONELY_VALUE for w, t in tl.result.invalid): break

    return seconds, " ".join(words[:used]), " ".join(words[used:])

if __name__ == "__main__":
    print(extract("100 hr 10 seconds aweawdawdwadawdawdawd"))
    print(extract("100 hr 10 10"))
    print(extract("100 hr 10"))
    print(extract("100 hr 10 seconds hours"))
    print(extract("10 this is the reason"))
    print(extract("10.2 this is the reason"))
    print(extract("10.9s this is the reason"))
    print(extract("10,9 this is the reason"))
    print(extract("10,9s this is the reason"))
    print(extract("100h10s"))
    print(extract("100hr10sec"))
    print(extract("100 hours 10 seconds this is a test about 100 hours and 10 seconds, not like 200 hours or something"))
    print(extract("200 hours ok this is actually 200 hours"))
    print(extract("100 hours 100 hours wow you can stack them"))
    print(extract("wow so empty"))
    print(extract("2s * 5s"))
    print(extract("2s + 2s")) # 4, noted
    print(extract("2s - 2s")) # 4??? why?????
    print(extract("2s = 2s"))
    print(extract("2s 2m"))
    print(extract("2s ** 2s"))
    print(extract("2s ^ 2s"))
    print(extract("2s ^ 2s"))
    print(extract("2s, 2s")) # 4, noted
    print(extract("2s and 2s")) # 4, noted
    print(extract("2s und 2s"))
    print(extract("2s with 2s"))
    print(extract("2s but 2s"))
    print(extract("2s & 2s")) # 4, noted
    print(extract("2s plus 2s")) # 2, noted
    print(extract("2_000s"))
    print(extract("2s.")) # all good
    print(extract("2s.."))
    print(extract("2s..."))
    print(extract("2s,")) # all good
    print(extract("2s,,"))
    print(extract("2s,,,"))
    print(extract("hour"))
    print(extract("1 hours"))
    print(extract("11 hour"))
    print(extract("2s. 2sec. 2seconds.")) # all good
    print(extract("20 seconds and this is the reason")) # raaaaaaaaaah
    print(extract("-20 seconds"))