#!/usr/bin/env python3
"""Blogger に記事を投稿・更新するスクリプト（Blogger API v3）。

必要な環境変数（クラウド環境の設定で登録。チャットには貼らないこと）:
  BLOGGER_CLIENT_ID      OAuth クライアント ID
  BLOGGER_CLIENT_SECRET  OAuth クライアント シークレット
  BLOGGER_REFRESH_TOKEN  スコープ https://www.googleapis.com/auth/blogger のリフレッシュトークン

使い方:
  python3 scripts/blogger_post.py check
  python3 scripts/blogger_post.py list [--n 10]
  python3 scripts/blogger_post.py post --title "タイトル" --labels 活動報告 --file 本文.html [--draft]
  python3 scripts/blogger_post.py update --post-id ID [--title ...] [--labels ...] [--file ...]
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request, urllib.error

BLOG_URL = "https://niiza-yasuragi.blogspot.com/"
API = "https://www.googleapis.com/blogger/v3"


def access_token():
    missing = [k for k in ("BLOGGER_CLIENT_ID", "BLOGGER_CLIENT_SECRET", "BLOGGER_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        sys.exit("環境変数が未設定です: " + ", ".join(missing))
    data = urllib.parse.urlencode({
        "client_id": os.environ["BLOGGER_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    return call("POST", "https://oauth2.googleapis.com/token", raw=data, token=None)["access_token"]


def call(method, url, body=None, raw=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        raw = json.dumps(body).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=raw, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        sys.exit("APIエラー %s: %s" % (e.code, e.read().decode()[:800]))


def blog_id(token):
    return call("GET", API + "/blogs/byurl?" + urllib.parse.urlencode({"url": BLOG_URL}), token=token)["id"]


def read_body(path):
    html = open(path, encoding="utf-8").read()
    return re.sub(r"^\s*<!--.*?-->\s*", "", html, flags=re.S)  # 先頭のメモ用コメントを除去


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p_list = sub.add_parser("list"); p_list.add_argument("--n", type=int, default=10)
    for name in ("post", "update"):
        p = sub.add_parser(name)
        p.add_argument("--title", required=(name == "post"))
        p.add_argument("--labels", nargs="*")
        p.add_argument("--file", required=(name == "post"))
        if name == "post":
            p.add_argument("--draft", action="store_true")
        else:
            p.add_argument("--post-id", required=True)
    a = ap.parse_args()

    tok = access_token()
    bid = blog_id(tok)
    if a.cmd == "check":
        b = call("GET", "%s/blogs/%s" % (API, bid), token=tok)
        print("OK:", b["name"], b["url"], "blogId=" + bid)
    elif a.cmd == "list":
        r = call("GET", "%s/blogs/%s/posts?maxResults=%d&fetchBodies=false" % (API, bid, a.n), token=tok)
        for it in r.get("items", []):
            print(it["published"], it["id"], it["title"], it.get("labels", []), it["url"])
    elif a.cmd == "post":
        body = {"kind": "blogger#post", "title": a.title, "content": read_body(a.file)}
        if a.labels:
            body["labels"] = a.labels
        q = "?isDraft=true" if a.draft else ""
        r = call("POST", "%s/blogs/%s/posts/%s" % (API, bid, q), body=body, token=tok)
        print("投稿しました:", r.get("id"), r.get("url") or "(下書き)")
    elif a.cmd == "update":
        body = {}
        if a.title: body["title"] = a.title
        if a.labels is not None: body["labels"] = a.labels
        if a.file: body["content"] = read_body(a.file)
        r = call("PATCH", "%s/blogs/%s/posts/%s" % (API, bid, a.post_id), body=body, token=tok)
        print("更新しました:", r.get("id"), r.get("url"))


if __name__ == "__main__":
    main()
