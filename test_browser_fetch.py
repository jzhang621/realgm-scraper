"""
Quick test script to verify browser fetcher can bypass Cloudflare.
"""

import logging
import fetcher_browser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s  %(message)s',
    datefmt='%H:%M:%S'
)

# Test URL that was previously blocked
test_url = "https://basketball.realgm.com/player/Marvin-Coleman-II/Summary/103906"

print(f"\nTesting browser fetcher on: {test_url}\n")
print("=" * 60)

try:
    html = fetcher_browser.get(test_url, use_cache=False)
    print(f"\n✅ SUCCESS! Fetched {len(html)} bytes")
    print(f"\nFirst 500 characters of HTML:")
    print("-" * 60)
    print(html[:500])
    print("-" * 60)

    # Check if we got real content (not Cloudflare challenge)
    if "Just a moment" in html:
        print("\n⚠️  WARNING: Got Cloudflare challenge page")
    elif "player-bio" in html or "player-name" in html:
        print("\n✅ SUCCESS: Got real player page content!")
    else:
        print(f"\n⚠️  Got HTML but doesn't look like player page")

except Exception as e:
    print(f"\n❌ ERROR: {e}")

finally:
    fetcher_browser.close()
    print("\n" + "=" * 60)
    print("Test complete\n")
