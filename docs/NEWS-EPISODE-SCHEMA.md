# News episode schema — `briefs/news/news-YYYYMMDD.json`

```json
{
 "id": "news-20261027",            // news-YYYYMMDD (Nepal date)
 "episode": 1,                      // running episode number
 "date": "2026-10-27",
 "title": "Tech News with G. Dai — Episode 1",
 "intro": "Namaste! Welcome to ...",            // spoken, 12–30 words
 "stories": [                                   // 5 by default, 5–8 allowed
  {
   "tag": "Cricket tech",                       // 1–2 words
   "region": "NEPAL",                           // NEPAL | WORLD
   "headline": "NPL brings DRS to every match", // ≤ 42 chars, shown on screen
   "kit": "drs",                                // drs ai chip space drone robot phone nepal globe ev app cyber
   "stat": {"value": 2, "prefix": "", "suffix": " reviews", "label": "per team, per innings"},  // optional, real number only
   "vo": "Big moment for Nepal cricket! ...",   // spoken, 22–38 words, numbers in words
   "source": "Kathmandu Post, Himalayan Times", // shown on screen
   "urls": ["https://..."]                      // pages actually opened
  }
 ],
 "outro": "That's your tech brief for today ...",
 "caption": "...",                              // ≤ 900 chars, says G. Dai is AI-generated
 "hashtags": ["#TechNews", "#NepalTech"]        // 6–8
}
```

Rendered by `gr/produce/newsroom/build_news.py` (premium newsroom template, G. Dai presenter, OmniVoice voice cloned
from `assets/voice/gdai_ref.wav`). Published at the 18:00 NPT slot.
