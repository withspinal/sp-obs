import pytest
from typing import Dict, Any


@pytest.fixture
def sample_response_attributes() -> Dict[str, Any]:
    """Perplexity response attributes (attributes only) taken from an actual span."""
    return {
        "spinal.provider": "perplexity",
        "content-type": "application/json",
        "content-encoding": "gzip",
        "http.status_code": 200,
        "http.url": "https://api.perplexity.ai/chat/completions",
        "http.host": "api.perplexity.ai",
        "spinal.response.size": 4402,
        "spinal.response.streaming": False,
        "model": "sonar",
        "messages": [
            {
                "role": "user",
                "content": "What were the results of the 2025 French Open Finals?",
            }
        ],
        "id": "78e68e06-1fb0-4a15-9836-b5aef319c37b",
        "created": 1757324531,
        "usage": {
            "prompt_tokens": 13,
            "completion_tokens": 347,
            "total_tokens": 360,
            "search_context_size": "low",
            "cost": {
                "input_tokens_cost": 0,
                "output_tokens_cost": 0,
                "request_cost": 0.005,
                "total_cost": 0.005,
            },
        },
        "citations": [
            "https://www.cbssports.com/tennis/news/2025-french-open-results-schedule-as-jannik-sinner-faces-carlos-alcaraz-coco-gauff-earns-first-title/",
            "https://www.tennis.com/news/articles/who-were-the-winners-and-losers-at-2025-roland-garros",
            "https://en.wikipedia.org/wiki/2025_French_Open_%E2%80%93_Men's_singles",
            "https://www.youtube.com/watch?v=H52VQbqUIF0",
            "https://en.wikipedia.org/wiki/2025_French_Open_%E2%80%93_Men's_singles_final",
        ],
        "search_results": [
            {
                "title": "2025 French Open: Results, schedule as Jannik Sinner faces Carlos ...",
                "url": "https://www.cbssports.com/tennis/news/2025-french-open-results-schedule-as-jannik-sinner-faces-carlos-alcaraz-coco-gauff-earns-first-title/",
                "date": "2025-06-07",
                "last_updated": "2025-09-08",
                "snippet": (
                    "A new women's champion has been crowned after Coco Gauff rallied to take down "
                    "Aryna Sabalenka in a three-set thriller in the final at Roland ..."
                ),
            },
            {
                "title": "Who were the winners and losers at 2025 Roland Garros?",
                "url": "https://www.tennis.com/news/articles/who-were-the-winners-and-losers-at-2025-roland-garros",
                "date": "2025-06-09",
                "last_updated": "2025-08-29",
                "snippet": (
                    "Babora Krejčíková has won the title at Roland Garros, Karolina Muchova is a former "
                    "runner-up, Petra Kvitova is a two-time semifinalist in Paris."
                ),
            },
            {
                "title": "2025 French Open – Men's singles - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/2025_French_Open_%E2%80%93_Men's_singles",
                "date": "2025-04-27",
                "last_updated": "2025-09-07",
                "snippet": (
                    "Defending champion Carlos Alcaraz defeated Jannik Sinner in the final, 4–6, 6–7, "
                    "6–4, 7–6, 7–6 to win the men's singles tennis title at the 2025 French Open. ..."
                ),
            },
            {
                "title": "Highlights Sabalenka vs Gauff Final | Roland-Garros 2025 - YouTube",
                "url": "https://www.youtube.com/watch?v=H52VQbqUIF0",
                "date": "2025-06-07",
                "last_updated": "2025-08-29",
                "snippet": (
                    "Watch the highlights of the 2025 Women's singles Final between Aryna Sabalenka "
                    "and Coco Gauff. Sponsored by Emirates."
                ),
            },
            {
                "title": "2025 French Open – Men's singles final - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/2025_French_Open_%E2%80%93_Men's_singles_final",
                "date": "2025-06-08",
                "last_updated": "2025-09-04",
                "snippet": (
                    "After 5 hours and 29 minutes of play, Alcaraz defeated Sinner 4–6, 6–7, 6–4, 7–6, 7–6 , "
                    "in the longest French Open final in history and the second-longest major final, behind "
                    "only the 2012 Australian Open men's singles final."
                ),
            },
        ],
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": (
                        "The 2025 French Open finals resulted in Coco Gauff winning the women's singles title "
                        "by defeating Aryna Sabalenka in a three-set match. On the men's side, defending "
                        "champion Carlos Alcaraz won an epic final against Jannik Sinner, overcoming a two-set "
                        "deficit to claim the title in a record 5 hours and 29 minutes match, the longest "
                        "French Open final in history and the second-longest major final overall[1][3][5].\n\n"
                        "More details:\n- **Women's final:** Coco Gauff, aged 21, rallied from behind to defeat "
                        "Aryna Sabalenka. This was Gauff's second Grand Slam title, her first being the 2023 "
                        "US Open, also over Sabalenka[1][4].\n- **Men's final:** Carlos Alcaraz defeated Jannik Sinner 4–6, "
                        "6–7^(4–7), 6–4, 7–6^(7–3), 7–6^(10–2). Alcaraz saved three championship points and "
                        "became only the third man in the Open Era to win a major after facing championship "
                        "points down. This was Alcaraz's second French Open title and fifth major overall. Both "
                        "players served for the championship during the match but were broken. The match was notable "
                        "for being the first French Open singles final decided by a final-set tiebreak and the first "
                        "major men's final contested by two players born in the 2000s[3][5].\n- The men's final was hailed as a historic "
                        'match that will resonate in the global sports community for a long time, likened to the heights of the "Big Four" '
                        "rivalry era in tennis[2]."
                    ),
                },
                "delta": {
                    "role": "assistant",
                    "content": "",
                },
            }
        ],
    }
