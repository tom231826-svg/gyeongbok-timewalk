# 경복궁 3D 에셋 수집 매니페스트

작성일: 2026-07-04
MVP 우선 대상: 근정전 · 근정문 · 행각(월랑) · 광화문 (근정전 앞마당 씬)

---

## 1. 확보 완료 (직접 다운로드 성공, `근정문_근정전-일대_data.go.kr/` 폴더)

data.go.kr 파일데이터는 **로그인 없이 다운로드 가능** (다운로드 버튼 URL 패턴: `https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=<ID>&fileDetailSn=1&insertDataPrcus=N`).

| 파일명 | 건물 | 형식·구성 | 출처 URL | 공공누리 유형 | 크기 |
|---|---|---|---|---|---|
| 경복궁_근정문및행각_서월랑_실측모델링.zip | 근정문 서월랑 (근정문 서쪽 회랑) | FBX(Binary, v7500) 1개 파일, 텍스처 1장(`GJM_W_WR_L_TXTR.jpg`) FBX 내부 임베드, 별도 텍스처 파일 없음 | https://www.data.go.kr/data/15092141/fileData.do | 미확인 (페이지 표기: "이용허락범위 제한 없음"만 확인, 공공누리 유형 명시 없음) | 28,194,916 bytes (약 26.9MB) |
| 경복궁_근정문_동월랑_실측모델링.zip | 근정문 동월랑 (근정문 동쪽 회랑) | FBX(Binary, v7500) 1개 파일, 텍스처 1장(`GJM_E_WR_L_TXTR.jpg`) FBX 내부 임베드 | https://www.data.go.kr/data/15092142/fileData.do | 미확인 (동일) | 29,776,073 bytes (약 28.4MB) |
| 경복궁_근정문및행각_동행각_실측모델링.zip | 근정문 및 행각 — 동행각 (근정전 마당 동쪽 회랑, 융문루 인접 구간) | FBX(Binary, v7500) 1개 + `img_opentype01.png`(1.7KB, 안내판 폰트 텍스처로 추정) 부속 1개, 텍스처 2장(`GJM_E_HG_TXTR.jpg` 외벽 + `GJM_E_HG_in1_TXTR.jpg` 내부) FBX 내부 임베드 | https://www.data.go.kr/data/15115257/fileData.do | 미확인 (동일) | 212,449,190 bytes (약 202.6MB) — 파일명은 "저용량"이지만 실제 용량은 큼 |

**폴리곤 규모**: 바이너리 FBX라 텍스트 파싱으로 정확한 폴리곤 수를 뽑지 못했음 (Blender 등으로 열어 확인 필요). 참고 신호: 임베드된 JPEG 마커 개수가 서월랑 3개, 동월랑 5개, 동행각 57개로 동행각 쪽이 압도적으로 무거움 — 목조 부재(공포·서까래 등) 디테일이 많아 텍스처/지오메트리 밀도가 높은 것으로 추정.

**전부 국가유산청 제공, "국가유산청_경복궁 OO 3D 실측모델링" 명명 규칙.**

---

## 2. 근정전 일대 — URL만 확보 (미다운로드, data.go.kr 직접 다운로드 가능 확인됨)

아래는 같은 다운로드 방식(`fileDownload.do?atchFileId=...`)으로 로그인 없이 받을 수 있는 것을 페이지 확인만 하고 실제 다운로드는 하지 않은 항목. MVP 2순위.

| 데이터셋 | 형식 | 출처 URL | atchFileId |
|---|---|---|---|
| 경복궁 근정문및행각 서행각 실측모델링 | FBX | https://www.data.go.kr/data/15115260/fileData.do | FILE_000000002746239 |
| 경복궁 흥례문동행각 실측모델링 | FBX | https://www.data.go.kr/data/15115258/fileData.do | FILE_000000002746237 |
| 경복궁 흥례문서행각 실측모델링 | FBX | https://www.data.go.kr/data/15115259/fileData.do | FILE_000000002746238 |
| 경복궁 건숙문 3D 실측모델링 | FBX/OBJ 계열 | https://www.data.go.kr/data/15092144/fileData.do | FILE_000000002459945 |
| 경복궁 사정문 3D 실측모델링 | FBX/OBJ 계열 | https://www.data.go.kr/data/15092148/fileData.do | FILE_000000002459956 |

다운로드 URL 조립법: `https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=<atchFileId>&fileDetailSn=1&insertDataPrcus=N`

---

## 3. 근정전 일대 이외 — data.go.kr에서 발견된 참고용 (미다운로드)

경복궁 전체로는 data.go.kr에 **총 250건 검색 결과 중 파일데이터 242건**이 있음 (건물별 실측모델링 다수). 근정전 앞마당 MVP와 직접 관련 없는 건물 예시:

- 경복궁 사정전 실측모델링 — https://www.data.go.kr/data/15115294/fileData.do
- 경복궁 경회루 실측모델링 — https://www.data.go.kr/data/15115251/fileData.do
- 경복궁 강녕전 실측모델링 — https://www.data.go.kr/data/15115247/fileData.do
- 경복궁 자선당 실측모델링 — https://www.data.go.kr/data/15115295/fileData.do
- 경복궁 교태전 동행 실측모델링 — https://www.data.go.kr/data/15115267/fileData.do
- 경복궁 비현각 실측모델링 — https://www.data.go.kr/data/15115249/fileData.do
- 경복궁 유화문 실측모델링 — https://www.data.go.kr/data/15115277/fileData.do
- 경복궁 장안당 동행각 실측모델링 — https://www.data.go.kr/data/15115282/fileData.do
- 경복궁 집경당 서행각 실측모델링 — https://www.data.go.kr/data/15115279/fileData.do
- (그 외 다수, 전체 목록은 https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=%EA%B2%BD%EB%B3%B5%EA%B6%81 에서 "FILE" 필터로 조회)

참고 문서: 국가유산청_국가유산 3D 원형 정보자원 목록_20231231 (전체 3D 자원 리스트 PDF/파일) — https://www.data.go.kr/data/15147467/fileData.do — 어떤 유산에 3D 자산이 존재하는지 전수 확인할 때 유용.

근정전 부속 유물(건물이 아닌 소품, 참고용): 국보_경복궁_근정전_그릇(https://www.data.go.kr/data/15135214/fileData.do), 도끼(15135208), 부채(15135210) 등 — 근정전 내부 향로·조명·백자 등 소품 3D 스캔이 별도로 존재하나 이번 수집 범위(건물 지오메트리) 밖이라 미다운로드.

---

## 4. 근정전 본채 · 광화문 — 로그인 없이 다운로드 불가, 정식 "이용신청" 필요 (digital.khs.go.kr)

**중요 발견**: 근정전(건물 자체)과 광화문의 3D 에셋은 data.go.kr에는 없고, 국가유산 디지털 서비스(digital.khs.go.kr)의 "3D 에셋 서비스" 카탈로그에만 존재함. 이 사이트는 로그인 자체는 강제하지 않지만(코드상 로그인 체크가 비활성화돼 있음), **다운로드 버튼을 누르면 매번 "이용신청(일반)" 팝업 양식을 실제로 제출해야만** 파일이 열림. 자동화/우회 없이 여기서 멈추고 아래 절차만 기록함.

### 확인된 파일
- **근정전**: 파일명 `국보_경복궁_근정전.zip` (건조물, 국보 지정)
  - 카탈로그: https://digital.khs.go.kr/heritage/catalog.do?order=1&index=1
  - 상세페이지: `https://digital.khs.go.kr/heritage/catalogDetail.do?order=1&index=1&id=13928228083859100002&type=1&hrtg=경복궁`
- **광화문**: uid `13928228084127100040` (동일 카탈로그 내, 사적)
  - 상세페이지: `https://digital.khs.go.kr/heritage/catalogDetail.do?order=1&index=1&id=13928228084127100040&type=1&hrtg=경복궁`
- **근정문및행각** (근정문·행각·융문루·융무루·월화문·일화문 개별 항목도 이 카탈로그에 별도 존재 — data.go.kr 파일과 별개의 KHS 전용 버전일 가능성 있음, 미확인)

### 필요한 수동 절차 (사용자 본인이 진행해야 함)
1. 위 상세페이지 접속 → "이용 신청하기" 버튼 클릭
2. 팝업 양식("이용신청(일반)") 작성:
   - 연령대 선택 (10대~60대 이상)
   - 이메일 입력
   - 신청자구분 선택 (일반인/학생/교사/회사원/공무원/기타)
   - 사용목적 선택 (연구/교육/방송/전시/**상업**/출판/기타) — 상업 서비스 목적이면 "상업" 선택
   - 상세목적 서술 (필수, 자유 텍스트)
   - 출처표시 정책 동의 체크 (출처는 반드시 "국가유산청"으로 표기해야 함)
   - 수집정보 활용 동의 체크 (거부 시 이용 불가할 수 있음)
3. 제출 후 승인/발급 절차가 있는지는 확인 못함 (신청서 제출까지만 코드 레벨에서 확인, 실제 승인 소요시간·즉시발급 여부는 실사용자가 신청해봐야 알 수 있음)
4. 라이선스·공공누리 유형은 이 신청 절차를 실제로 마쳐야 화면에서 확인 가능 — 이번 수집에서는 신청서를 대신 제출하지 않았으므로 **라이선스 유형 미확인** 상태

---

## 5. 결론 (MVP 진행 가능성)

- **근정문(서월랑·동월랑) + 근정문및행각 동행각은 확보 완료** — 근정전 앞마당의 좌우 진입부/회랑 지오메트리는 이미 손에 있음.
- **근정전 본채와 광화문은 파일 자체는 확인되지만("국보_경복궁_근정전.zip" 등 파일명까지 특정됨) 즉시 다운로드는 불가** — 사용자 본인이 digital.khs.go.kr에서 이메일 등 개인정보를 넣는 "이용신청" 양식을 제출해야 함. 상업적 사용목적을 명시해야 하므로 신청 문구를 신중히 작성할 필요 있음(§4 참고, MASTER_PLAN.md의 국가유산청 디지털정보담당관실 문의와 연계 권장).
- 근정전 본채 3D 없이는 "근정전 앞마당" MVP 씬의 핵심 피사체가 빠진 상태이므로, **§4의 이용신청을 최우선으로 사용자가 직접 처리**하는 것이 MVP 진행의 다음 관문. 신청서 승인 소요 시간을 알 수 없으므로 최대한 빨리 신청 필요.
