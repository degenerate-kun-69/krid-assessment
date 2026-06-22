
"""
dev.py — One-command local development launcher.

Starts uvicorn + pinggy.io tunnel together. The public tunnel URL is
automatically set as BASE_URL so Twilio can reach your media assets
and webhook endpoint.

Why Pinggy? Unlike localtunnel, pinggy does not have an anti-phishing
splash screen on the first visit, which would break Twilio's ability to
download media assets.

Usage:
    python dev.py                 # default port 8080
    python dev.py --port 3000     # custom port
    python dev.py --no-tunnel     # skip tunnel, just run uvicorn

Requirements:
    ssh (built into macOS/Linux)
"""

import argparse
import os
import subprocess
import sys
import re
import time
import threading


def _read_tunnel_url(process, result: dict, ready_event: threading.Event):
    """
    Read pinggy stdout in a background thread to capture the public URL.
    Pinggy prints multiple lines, we want the one starting with https://
    and ending in pinggy.net or similar.
    """
    try:
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            
            
            match = re.search(r"(https://\S+\.pinggy\.(link|net))", line)
            if match:
                result["url"] = match.group(1)
                ready_event.set()
                break
    except Exception:
        ready_event.set()


def start_tunnel(port: int) -> tuple:
    """
    Start a pinggy tunnel via ssh and return (public_url, subprocess).
    """
    print(f"[dev] Starting pinggy.io tunnel on port {port} via SSH...")

    try:
        
        
        process = subprocess.Popen(
            ["ssh", "-p", "443", "-o", "StrictHostKeyChecking=no", f"-R0:localhost:{port}", "a.pinggy.io"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("[dev] ⚠ SSH not found on your system. Cannot start pinggy tunnel.")
        print("[dev]   Falling back to local-only mode (no tunnel).")
        return "", None

    
    result = {}
    ready = threading.Event()
    reader = threading.Thread(target=_read_tunnel_url, args=(process, result, ready), daemon=True)
    reader.start()

    ready.wait(timeout=120)











































































 
    public_url = result.get("url", "")
    if not public_url:
        print("[dev] ⚠ Timed out waiting for pinggy URL. (Check your internet connection)")
        print("[dev]   Falling back to local-only mode (no tunnel).")
        process.terminate()
        return "", None

    print(f"[dev] ✅ Tunnel active: {public_url}")
    print(f"[dev]")
    print(f"[dev] ┌────────────────────────────────────────────────────────────┐")
    print(f"[dev] │  PUBLIC URL: {public_url:<47s}│")
    print(f"[dev] │                                                            │")
    print(f"[dev] │  Webhook:   {public_url}/api/webhooks/whatsapp")
    print(f"[dev] │  Media:     {public_url}/media/minecraft/castle.png")
    print(f"[dev] │  Dashboard: http://localhost:{port}")
    print(f"[dev] └────────────────────────────────────────────────────────────┘")
    print(f"[dev]")
    print(f"[dev] 📋 Copy the webhook URL above into Twilio Console:")
    print(f"[dev]    Messaging → WhatsApp Sandbox → 'When a message comes in'")
    print(f"[dev]")
    print(f"[dev] ℹ️  Pinggy free tunnels expire after 60 minutes. Restart dev.py to get a new one.")
    print()

    return public_url, process


def main():
    parser = argparse.ArgumentParser(description="Krid AI local dev launcher")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on (default: 8080)")
    parser.add_argument("--no-tunnel", action="store_true", help="Skip tunnel, just run uvicorn")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    tunnel_process = None

    
    public_url = ""
    if not args.no_tunnel:
        public_url, tunnel_process = start_tunnel(args.port)

    
    if public_url:
        os.environ["BASE_URL"] = public_url
        print(f"[dev] BASE_URL set to: {public_url}")
    else:
        fallback = f"http://localhost:{args.port}"
        os.environ.setdefault("BASE_URL", fallback)
        print(f"[dev] BASE_URL: {os.environ['BASE_URL']}")

    print(f"[dev] Starting uvicorn on {args.host}:{args.port}...")
    print()

    
    import uvicorn

    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        pass
    finally:
        
        if tunnel_process:
            tunnel_process.terminate()
            tunnel_process.wait(timeout=5)
            print("\n[dev] Tunnel closed.")


if __name__ == "__main__":
    main()
