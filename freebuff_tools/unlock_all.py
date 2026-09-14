#!/usr/bin/env python3
"""清掉所有账号当前锁定的 session。

背景：上游一个账号同一时间只锁一个模型的 session（1 小时）。
切换模型时若旧 session 还活着，admission 会返回 409 model_locked，
而 freebuff2api 的 worker.js 把 model_locked 直接判为「额度耗尽」并跳过该号，
四个号全锁着就会表现成「账号池耗尽」的报错。

用法：python unlock_all.py
DELETE 会触发 freebucksRefundPending（未消耗部分退回），所以解锁不亏。

只依赖标准库。
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRED = Path(__file__).with_name("freebuff_credentials.json")
BASE = "https://www.codebuff.com"
UA = "ai-sdk/openai-compatible/1.0.25/codebuff"


def api(token, method, path, inst=None):
    headers = {"Authorization": f"Bearer {token}", "User-Agent": UA}
    if inst:
        headers["x-freebuff-instance-id"] = inst
    req = urllib.request.Request(BASE + path, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except Exception as exc:  # 网络异常不致命，继续处理下一个号
        return "ERR", str(exc)


def main():
    if not CRED.exists():
        print(f"找不到凭据文件：{CRED}")
        print("先跑 python extract_freebuff.py login")
        return 1

    data = json.loads(CRED.read_text(encoding="utf-8"))
    accounts = data.get("accounts") or {}
    if not accounts:
        print("凭据文件里没有账号")
        return 1

    freed = 0
    for key, acct in accounts.items():
        token = acct.get("authToken")
        email = acct.get("email") or key
        if not token:
            print(f"[{email}] 无 authToken，跳过")
            continue

        status, body = api(token, "GET", "/api/v1/freebuff/session")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {}

        if status == 200 and parsed.get("status") == "active":
            inst = parsed.get("instanceId")
            model = parsed.get("model")
            st2, b2 = api(token, "DELETE", "/api/v1/freebuff/session", inst=inst)
            print(f"[{email}] 锁定 {model} -> DELETE {st2} {b2[:100]}")
            freed += 1
        else:
            state = parsed.get("status") or parsed.get("error") or body[:60]
            print(f"[{email}] 无活跃 session（HTTP {status} / {state}）")

    print(f"\n共释放 {freed} 个账号。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
