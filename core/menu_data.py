from typing import Literal, TypedDict


class MenuItem(TypedDict):
    name: str
    category: Literal["출출이", "본격이", "마지막잔이", "술"]
    price: int
    spicy: int
    ingredients: list[str]
    description: str
    owner: Literal["삼촌", "이모", "공통"]
    is_signature: bool


MENU: dict[str, MenuItem] = {
    "삼촌네 오뎅탕": {
        "name": "삼촌네 오뎅탕",
        "category": "출출이",
        "price": 8000,
        "spicy": 1,
        "ingredients": ["오뎅", "무", "대파"],
        "description": "무 푹 우린 진한 국물. 속 풀릴 때 좋아유.",
        "owner": "삼촌",
        "is_signature": False,
    },
    "이모표 계란말이": {
        "name": "이모표 계란말이",
        "category": "출출이",
        "price": 9000,
        "spicy": 0,
        "ingredients": ["계란", "대파", "당근"],
        "description": "대파 듬뿍 넣은 손말이. 폭신혀.",
        "owner": "이모",
        "is_signature": False,
    },
    "노가리 한 마리": {
        "name": "노가리 한 마리",
        "category": "출출이",
        "price": 5000,
        "spicy": 0,
        "ingredients": ["노가리"],
        "description": "바삭하게 구운 통노가리. 마요+간장 곁들임.",
        "owner": "공통",
        "is_signature": False,
    },
    "이모 손맛 골뱅이무침": {
        "name": "이모 손맛 골뱅이무침",
        "category": "본격이",
        "price": 18000,
        "spicy": 2,
        "ingredients": ["골뱅이", "오이", "양파", "소면"],
        "description": "새콤달콤 매콤. 소면 사리 포함.",
        "owner": "이모",
        "is_signature": True,
    },
    "불맛 제육볶음": {
        "name": "불맛 제육볶음",
        "category": "본격이",
        "price": 16000,
        "spicy": 3,
        "ingredients": ["돼지고기", "양파", "고추장"],
        "description": "직화로 볶은 매콤 제육. 상추쌈 곁들임.",
        "owner": "이모",
        "is_signature": False,
    },
    "묵은지 김치찜": {
        "name": "묵은지 김치찜",
        "category": "본격이",
        "price": 19000,
        "spicy": 2,
        "ingredients": ["묵은지", "통목살", "두부"],
        "description": "3년 묵은지에 통목살 푹 끓임.",
        "owner": "이모",
        "is_signature": False,
    },
    "양념 닭발": {
        "name": "양념 닭발",
        "category": "본격이",
        "price": 15000,
        "spicy": 4,
        "ingredients": ["무뼈닭발", "양파", "고추"],
        "description": "무뼈닭발. 매운맛 주의.",
        "owner": "이모",
        "is_signature": False,
    },
    "콩나물 라면": {
        "name": "콩나물 라면",
        "category": "마지막잔이",
        "price": 6000,
        "spicy": 1,
        "ingredients": ["라면", "콩나물", "계란(옵션)"],
        "description": "술 마시고 먹는 그 라면. 계란 추가 +1,000원.",
        "owner": "공통",
        "is_signature": False,
    },
    "소주": {
        "name": "소주",
        "category": "술",
        "price": 5000,
        "spicy": 0,
        "ingredients": ["참이슬 또는 처음처럼"],
        "description": "참이슬/처음처럼 중 선택",
        "owner": "공통",
        "is_signature": False,
    },
    "맥주": {
        "name": "맥주",
        "category": "술",
        "price": 5000,
        "spicy": 0,
        "ingredients": ["카스 또는 테라"],
        "description": "카스/테라 중 선택",
        "owner": "공통",
        "is_signature": False,
    },
    "막걸리": {
        "name": "막걸리",
        "category": "술",
        "price": 6000,
        "spicy": 0,
        "ingredients": ["장수막걸리"],
        "description": "장수막걸리",
        "owner": "공통",
        "is_signature": False,
    },
    "소맥 세트": {
        "name": "소맥 세트",
        "category": "술",
        "price": 9000,
        "spicy": 0,
        "ingredients": ["소주 1병 + 맥주 1병"],
        "description": "소주 1 + 맥주 1 세트",
        "owner": "공통",
        "is_signature": False,
    },
}

OFFICIAL_MENU_NAMES = list(MENU.keys())


def get_menu_by_category(category: str) -> list[MenuItem]:
    return [item for item in MENU.values() if item["category"] == category]


def get_menu_by_max_spicy(max_spicy: int) -> list[MenuItem]:
    return [item for item in MENU.values() if item["spicy"] <= max_spicy]


def get_signature_items() -> list[MenuItem]:
    return [item for item in MENU.values() if item["is_signature"]]


def is_valid_menu(name: str) -> bool:
    return name in MENU


def get_price(name: str) -> int | None:
    item = MENU.get(name)
    return item["price"] if item else None
