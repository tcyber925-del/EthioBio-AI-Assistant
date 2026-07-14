"""Benchmark diagram generation: quality and latency."""
import asyncio
import json
import time
from statistics import mean, median, stdev

import httpx

API_URL = "http://localhost:8000"

TOPICS = [
    ("cells", "Draw a plant cell with labeled organelles"),
    ("genetics", "Draw a Punnett square showing dominant and recessive traits"),
    ("photosynthesis", "Draw the light-dependent and light-independent reactions of photosynthesis"),
    ("human biology", "Draw the human heart with four chambers labeled"),
    ("ecology", "Draw a food web showing predator-prey relationships in a grassland ecosystem"),
]

def validate_svg(svg: str) -> dict:
    issues = []
    if not svg.strip():
        issues.append("empty SVG")
    if "<svg" not in svg:
        issues.append("missing <svg> tag")
    if "</svg>" not in svg:
        issues.append("missing </svg> tag")
    viewbox = "viewBox" in svg or ('width="' in svg and 'height="' in svg)
    if not viewbox:
        issues.append("no viewBox or width/height")
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "size_bytes": len(svg.encode("utf-8")),
    }

async def benchmark():
    async with httpx.AsyncClient(timeout=300) as client:
        results = []
        for i, (topic, prompt) in enumerate(TOPICS):
            print(f"\n[{i+1}/{len(TOPICS)}] {topic}: {prompt[:60]}...")
            for difficulty in ["beginner", "intermediate"]:
                payload = {
                    "prompt": prompt,
                    "topic": topic,
                    "difficulty": difficulty,
                }
                start = time.time()
                try:
                    resp = await client.post(f"{API_URL}/diagram/generate", json=payload)
                    elapsed = time.time() - start
                    data = resp.json()
                    svg = data.get("diagram_svg", "")
                    labels = data.get("labels", [])
                    quality = validate_svg(svg)
                    results.append({
                        "topic": topic,
                        "difficulty": difficulty,
                        "latency": round(elapsed, 2),
                        "status": resp.status_code,
                        "svg_valid": quality["valid"],
                        "svg_size_kb": round(quality["size_bytes"] / 1024, 1),
                        "label_count": len(labels),
                        "issues": quality["issues"],
                        "model_used": data.get("model_used", "unknown"),
                    })
                    status = "OK" if quality["valid"] else "ISSUES"
                    print(f"  [{difficulty}] {elapsed:.1f}s | {status} | {len(labels)} labels | {quality['size_bytes']//1024}KB | model={data.get('model_used','?')}")
                except Exception as e:
                    elapsed = time.time() - start
                    results.append({
                        "topic": topic,
                        "difficulty": difficulty,
                        "latency": round(elapsed, 2),
                        "status": 0,
                        "svg_valid": False,
                        "svg_size_kb": 0,
                        "label_count": 0,
                        "issues": [str(e)],
                        "model_used": "error",
                    })
                    print(f"  [{difficulty}] {elapsed:.1f}s | ERROR: {e}")

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    latencies = [r["latency"] for r in results if r["status"] == 200]
    if latencies:
        print("\nLatency (successful only):")
        print(f"  Mean:   {mean(latencies):.1f}s")
        print(f"  Median: {median(latencies):.1f}s")
        if len(latencies) > 1:
            print(f"  Stdev:  {stdev(latencies):.1f}s")
        print(f"  Min:    {min(latencies):.1f}s")
        print(f"  Max:    {max(latencies):.1f}s")

    valid = [r for r in results if r["svg_valid"]]
    print("\nSVG Quality:")
    print(f"  Valid:        {len(valid)}/{len(results)}")
    print(f"  Avg labels:   {mean([r['label_count'] for r in results]):.1f}")
    print(f"  Avg size:     {mean([r['svg_size_kb'] for r in results]):.1f}KB")

    issues = [r for r in results if not r["svg_valid"] and r["status"] == 200]
    if issues:
        print(f"\nIssues found in {len(issues)} diagrams:")
        for r in issues:
            print(f"  [{r['topic']}/{r['difficulty']}] {', '.join(r['issues'])}")

    errors = [r for r in results if r["status"] != 200]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            print(f"  [{r['topic']}/{r['difficulty']}] HTTP {r['status']}: {r['issues']}")

    print("\n" + "=" * 60)
    print("RAW RESULTS")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(benchmark())
