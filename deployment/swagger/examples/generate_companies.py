import json
import random
from datetime import datetime, timedelta

# 業界リスト
industries = ["IT・ソフトウェア", "製造業", "人材・派遣", "金融・保険", "不動産", "その他"]

# 都道府県リスト
prefectures = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
]

# 姓名リスト
last_names = ["田中", "山田", "佐藤", "鈴木", "高橋", "伊藤", "渡辺", "中村", "小林", "加藤", "吉田", "山本", "森", "松本", "井上"]
first_names_male = ["太郎", "次郎", "三郎", "健一", "誠", "隆", "明", "浩", "直樹", "健太", "大輔", "翔太", "拓也", "雄一", "正人"]
first_names_female = ["花子", "美咲", "優子", "恵美", "真由美", "明美", "由美子", "智子", "陽子", "美香", "愛", "さくら", "みどり", "ゆり", "あやか"]

# 企業名の接頭辞
company_prefixes = ["株式会社", "合同会社", "有限会社"]

# 企業名の中間部
company_middles = [
    "グローバル", "イノベーション", "テクノロジー", "ソリューション", "パートナーズ",
    "システム", "サービス", "ネットワーク", "クリエイティブ", "デジタル",
    "スマート", "アドバンス", "フューチャー", "ビジネス", "エンタープライズ",
    "プロフェッショナル", "コンサルティング", "マネジメント", "インテグレーション", "ダイナミック"
]

# 業界別の企業名サフィックス
industry_suffixes = {
    "IT・ソフトウェア": ["ソフト", "システムズ", "テック", "ラボ", "デジタル", "ネット", "ウェブ", "AI", "データ"],
    "製造業": ["製造", "工業", "産業", "マテリアル", "エンジニアリング", "プロダクツ", "ファクトリー", "製作所"],
    "人材・派遣": ["ヒューマン", "キャリア", "スタッフ", "リクルート", "ワークス", "人材", "ジョブ", "タレント"],
    "金融・保険": ["ファイナンス", "キャピタル", "インベストメント", "アセット", "保険", "証券", "トラスト", "バンク"],
    "不動産": ["不動産", "エステート", "プロパティ", "リアルティ", "ハウジング", "ビルディング", "デベロップメント"],
    "その他": ["サービス", "カンパニー", "グループ", "ホールディングス", "コーポレーション"]
}

def generate_company_name(industry, index):
    """企業名を生成"""
    prefix = random.choice(company_prefixes)
    middle = random.choice(company_middles)
    suffix = random.choice(industry_suffixes[industry])
    return f"{prefix}{middle}{suffix}"

def generate_executive():
    """役員情報を生成"""
    is_male = random.choice([True, False])
    last_name = random.choice(last_names)
    if is_male:
        first_name = random.choice(first_names_male)
    else:
        first_name = random.choice(first_names_female)
    
    name = f"{last_name}{first_name}"
    position = random.choice(["代表取締役", "代表取締役社長", "代表取締役CEO", "取締役", "取締役CTO", "専務取締役", "常務取締役"])
    
    # Facebook URLは60%の確率で持つ
    has_facebook = random.random() < 0.6
    facebook_url = f"https://facebook.com/{last_name}.{first_name.lower()}" if has_facebook else ""
    
    # LinkedIn URLは30%の確率で持つ
    has_linkedin = random.random() < 0.3
    other_sns_url = f"https://linkedin.com/in/{last_name}-{first_name.lower()}" if has_linkedin else ""
    
    return {
        "name": name,
        "position": position,
        "facebook_url": facebook_url,
        "other_sns_url": other_sns_url,
        "direct_email": "",
        "notes": ""
    }

def generate_companies(count=100):
    """企業データを生成"""
    companies = []
    
    for i in range(1, count + 1):
        industry = random.choice(industries)
        prefecture = random.choice(prefectures)
        
        # 都道府県から市区町村を生成
        if prefecture == "東京都":
            city = random.choice(["千代田区", "中央区", "港区", "新宿区", "渋谷区", "品川区", "目黒区", "世田谷区"])
        elif prefecture == "大阪府":
            city = random.choice(["大阪市", "堺市", "豊中市", "吹田市", "枚方市"])
        elif prefecture == "神奈川県":
            city = random.choice(["横浜市", "川崎市", "相模原市", "藤沢市", "鎌倉市"])
        elif prefecture == "愛知県":
            city = random.choice(["名古屋市", "豊田市", "岡崎市", "一宮市", "春日井市"])
        elif prefecture == "福岡県":
            city = random.choice(["福岡市", "北九州市", "久留米市", "春日市", "大野城市"])
        else:
            city = f"{prefecture.replace('県', '').replace('府', '').replace('都', '')}市"
        
        # 企業規模を業界に応じて設定
        if industry == "IT・ソフトウェア":
            employee_count = random.randint(10, 500)
            revenue = employee_count * random.randint(2000000, 10000000)
        elif industry == "製造業":
            employee_count = random.randint(50, 1000)
            revenue = employee_count * random.randint(3000000, 15000000)
        elif industry == "人材・派遣":
            employee_count = random.randint(20, 300)
            revenue = employee_count * random.randint(2500000, 8000000)
        elif industry == "金融・保険":
            employee_count = random.randint(30, 500)
            revenue = employee_count * random.randint(4000000, 20000000)
        elif industry == "不動産":
            employee_count = random.randint(10, 200)
            revenue = employee_count * random.randint(5000000, 25000000)
        else:
            employee_count = random.randint(10, 300)
            revenue = employee_count * random.randint(2000000, 10000000)
        
        # 設立年をランダムに設定（1980-2023年）
        established_year = random.randint(1980, 2023)
        
        # 企業名を生成
        company_name = generate_company_name(industry, i)
        
        # URLとメールアドレスを生成
        domain = company_name.replace("株式会社", "").replace("合同会社", "").replace("有限会社", "").replace(" ", "").lower()[:20]
        website_url = f"https://{domain}.co.jp"
        contact_email = f"info@{domain}.co.jp"
        
        # 電話番号を生成（地域に応じた市外局番）
        area_codes = {
            "東京都": "03", "大阪府": "06", "神奈川県": "045", "愛知県": "052",
            "福岡県": "092", "北海道": "011", "京都府": "075", "兵庫県": "078"
        }
        area_code = area_codes.get(prefecture, "03")
        phone = f"{area_code}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        
        # 役員情報を生成（1-3名）
        executives = []
        executive_count = random.randint(1, 3)
        for j in range(executive_count):
            executive = generate_executive()
            executive["id"] = i * 10 + j
            executive["direct_email"] = f"{executive['name'].replace(' ', '').lower()}@{domain}.co.jp"
            executives.append(executive)
        
        # NG企業は5%の確率
        is_global_ng = random.random() < 0.05
        
        # 日付を生成
        created_date = datetime(2025, 1, random.randint(1, 20), random.randint(8, 18), random.randint(0, 59), 0)
        updated_date = created_date + timedelta(days=random.randint(0, 20), hours=random.randint(0, 8))
        
        company = {
            "id": i,
            "name": company_name,
            "industry": industry,
            "employee_count": employee_count,
            "revenue": revenue,
            "prefecture": prefecture,
            "city": city,
            "established_year": established_year,
            "website_url": website_url,
            "contact_email": contact_email,
            "phone": phone,
            "notes": "",
            "is_global_ng": is_global_ng,
            "created_at": created_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": updated_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "executives": executives
        }
        
        companies.append(company)
    
    return companies

if __name__ == "__main__":
    companies = generate_companies(100)
    
    # JSONファイルに保存
    with open("companies_generated.json", "w", encoding="utf-8") as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(companies)} companies")
    
    # 統計情報を表示
    industry_counts = {}
    for company in companies:
        industry = company["industry"]
        industry_counts[industry] = industry_counts.get(industry, 0) + 1
    
    print("\n業界別企業数:")
    for industry, count in sorted(industry_counts.items()):
        print(f"  {industry}: {count}社")
    
    # Facebook URL保有率
    facebook_count = sum(1 for c in companies if any(e["facebook_url"] for e in c["executives"]))
    print(f"\nFacebook URL保有企業: {facebook_count}社 ({facebook_count*100/len(companies):.1f}%)")
    
    # NG企業数
    ng_count = sum(1 for c in companies if c["is_global_ng"])
    print(f"NG企業: {ng_count}社 ({ng_count*100/len(companies):.1f}%)")