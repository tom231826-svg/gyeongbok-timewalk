#!/bin/zsh
# data.go.kr에서 신청서 없이 받을 수 있는 경복궁 실측 스캔 추가 확보 → 웹용 변환까지 일괄.
# 근거: data/02_3d-assets/MANIFEST.md §2·§3 (직접 다운로드 URL 패턴 확인됨)
set -u
BASE=/Users/junkim/projects/gyeongbok-timewalk/data/02_3d-assets
EX=$BASE/extra
OUT=/Users/junkim/projects/gyeongbok-timewalk/prototype/assets/scans_csp
mkdir -p "$EX"

dl(){ # name atchFileId
  if [ -s "$EX/$1.zip" ]; then echo "SKIP $1 (이미 있음)"; return; fi
  curl -sL --max-time 1200 -o "$EX/$1.zip" \
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=$2&fileDetailSn=1&insertDataPrcus=N" \
    && echo "DL $1 $(stat -f%z "$EX/$1.zip") bytes" || echo "DL-FAIL $1"
}
scrape(){ curl -sL "https://www.data.go.kr/data/$1/fileData.do" | grep -oE 'FILE_[0-9]{15}' | head -1; }

dl seohaenggak FILE_000000002746239      # 근정문및행각 서행각 (근정전 마당 서쪽)
dl heung_e     FILE_000000002746237      # 흥례문 동행각
dl heung_w     FILE_000000002746238      # 흥례문 서행각
dl sajeongmun  FILE_000000002459956      # 사정문
for pair in "sajeongjeon:15115294" "gyeonghoeru:15115251" "gangnyeongjeon:15115247"; do
  name=${pair%%:*}; num=${pair##*:}
  ID=$(scrape "$num")
  if [ -n "$ID" ]; then dl "$name" "$ID"; else echo "SCRAPE-FAIL $name ($num)"; fi
done

python3 - <<'EOF'
import zipfile, os, glob
EX = "/Users/junkim/projects/gyeongbok-timewalk/data/02_3d-assets/extra"
for z in sorted(glob.glob(EX + "/*.zip")):
    base = os.path.splitext(os.path.basename(z))[0]
    out = f"{EX}/{base}.fbx"
    if os.path.exists(out):
        print("UNZ-SKIP", base); continue
    try:
        with zipfile.ZipFile(z) as zf:
            fbx = [i for i in zf.infolist() if i.filename.lower().endswith(".fbx")]
            if not fbx:
                print("UNZIP-NOFBX", base, [i.filename[-20:] for i in zf.infolist()][:5]); continue
            info = max(fbx, key=lambda i: i.file_size)   # 최대 파일 = 본 모델
            with zf.open(info) as s, open(out, "wb") as d:
                while True:
                    c = s.read(1 << 20)
                    if not c: break
                    d.write(c)
            print("UNZ", out, os.path.getsize(out) // 1048576, "MB")
    except Exception as e:
        print("UNZIP-FAIL", z, e)
EOF

conv(){ # name target texsize
  if [ ! -f "$EX/$1.fbx" ]; then echo "CONV-SKIP $1 (fbx 없음)"; return; fi
  /Applications/Blender.app/Contents/MacOS/Blender -b \
    -P /Users/junkim/projects/gyeongbok-timewalk/prototype/src/convert_csp.py -- \
    "$EX/$1.fbx" "$OUT" "$1" "$2" "$3" 2>&1 | grep -E '\[MAT\]|\[GLB\]|\[STATS\]'
}
conv seohaenggak   70000 2048
conv heung_e       50000 1024
conv heung_w       50000 1024
conv sajeongmun    40000 1024
conv sajeongjeon   60000 1536
conv gyeonghoeru   80000 2048
conv gangnyeongjeon 50000 1024
echo ALL-DONE
