from datetime import datetime
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
import re

app = Flask(__name__)
app.secret_key = "timesale_secret_key_security_123"

# 메모리 기반 데이터베이스 및 타임딜 설정
# sale_open_time: ISO 형식 (예시: 테스트를 위해 2026년 기준 넉넉하게 설정, 원하시면 문자열을 수정하세요)
sale_config = {
    "open_time": "2026-06-01T00:00:00"  # 이 시간 이후에만 구매 가능 (테스트 시 현재 시간보다 과거로 설정하면 즉시 열림)
}

products = {
    1: {"id": 1, "name": "리미티드 에디션 스니커즈", "price": 150000, "stock": 3},
    2: {"id": 2, "name": "한정판 후드티 굿즈", "price": 69000, "stock": 5},
}
orders = []

ADMIN_ID = "admin"
ADMIN_PW = "1234"

# ==================== 1. 사용자용 메인 페이지 (카운트다운 타이머 & 오픈 시간 제어) ====================
USER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>한정판 타임세일 서비스</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-6 flex flex-col min-h-screen">
    <div class="max-w-2xl mx-auto w-full bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex-1">
        
        <div class="text-center mb-6">
            <h1 class="text-3xl font-extrabold text-gray-900 tracking-tight">⚡ LIMITED TIME SALE</h1>
            <p class="text-gray-500 text-sm mt-1">한정판 굿즈 선착순 구매 서비스</p>
        </div>

        <!-- 타임딜 오픈 카운트다운 배너 -->
        <div id="timer-banner" class="mb-6 p-4 rounded-xl text-center font-semibold text-sm transition-all shadow-2xs bg-indigo-50 text-indigo-900 border border-indigo-100">
            ⏳ 오픈 대기 중: 남은 시간 계산 중...
        </div>

        <!-- 기능 1: 상품 및 잔여 재고 조회 -->
        <div class="mb-6 p-5 border border-gray-100 rounded-xl bg-gray-50/50">
            <div class="flex justify-between items-center mb-3">
                <h2 class="text-base font-bold text-gray-800">📌 1. 타임딜 상품 및 잔여 재고</h2>
                <button onclick="loadStatus()" class="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-100 transition">새로고침</button>
            </div>
            <div id="product-list" class="grid grid-cols-2 gap-3"></div>
        </div>

        <!-- 기능 2: 선착순 굿즈 구매 신청 (오픈 시간에 따라 활성화/비활성화) -->
        <div class="mb-6 p-5 border border-gray-100 rounded-xl bg-gray-50/50">
            <h2 class="text-base font-bold text-gray-800 mb-3">📌 2. 선착순 굿즈 구매 신청</h2>
            <form onsubmit="submitPurchase(event)" class="space-y-3">
                <div>
                    <label class="block text-xs font-semibold text-gray-600 mb-1">상품 선택</label>
                    <select id="purchase-product-id" class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"></select>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">구매자 이름</label>
                        <input type="text" id="buyer-name" required class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none" placeholder="한글 2글자 이상">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">연락처 (- 없이 숫자만)</label>
                        <input type="text" id="buyer-phone" required class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none" placeholder="01012345678">
                    </div>
                </div>
                <button type="submit" id="purchase-btn" class="w-full bg-gray-300 text-gray-500 font-semibold p-2.5 rounded-lg transition text-sm shadow-sm cursor-not-allowed" disabled>🔒 타임딜 오픈 대기 중</button>
            </form>
            <div id="purchase-result" class="mt-3 text-sm"></div>
        </div>

        <!-- 기능 3: 주문 접수 내역 조회 -->
        <div class="p-5 border border-gray-100 rounded-xl bg-gray-50/50">
            <h2 class="text-base font-bold text-gray-800 mb-3">📌 3. 내 주문 접수 내역 조회</h2>
            <div class="flex space-x-2 mb-3">
                <input type="text" id="search-name" placeholder="주문자 이름 입력" class="p-2.5 bg-white border border-gray-200 rounded-lg flex-1 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                <button onclick="searchOrders()" class="bg-gray-800 text-white px-4 py-2.5 rounded-lg hover:bg-gray-900 transition text-sm font-semibold">조회하기</button>
            </div>
            <div id="order-result" class="space-y-2"></div>
        </div>

    </div>

    <footer class="text-center mt-6 text-xs text-gray-400">
        &copy; 2026 Timesale Service. All rights reserved. 
        <a href="/admin/login" class="text-gray-300 hover:text-gray-600 ml-1 transition" title="관리자">.</a>
    </footer>

    <script>
        let serverOpenTime = null;

        async function loadStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            serverOpenTime = new Date(data.open_time).getTime();

            // 상품 목록 렌더링
            let html = '', selectHtml = '';
            for (let id in data.products) {
                let p = data.products[id];
                const isSoldOut = p.stock <= 0;
                html += `<div class="p-3 bg-white border border-gray-100 rounded-xl shadow-2xs">
                    <p class="font-bold text-gray-800 text-sm">${p.name}</p>
                    <p class="text-xs text-gray-500 mt-0.5">${p.price.toLocaleString()}원</p>
                    <p class="text-xs font-semibold mt-2 ${isSoldOut ? 'text-red-500' : 'text-indigo-600'}">
                        ${isSoldOut ? '🔴 품절' : `🟢 잔여: ${p.stock}개`}
                    </p>
                </div>`;
                if (!isSoldOut) {
                    selectHtml += `<option value="${p.id}">${p.name} (잔여: ${p.stock}개)</option>`;
                }
            }
            document.getElementById('product-list').innerHTML = html;
            document.getElementById('purchase-product-id').innerHTML = selectHtml || '<option value="">모든 상품 품절</option>';
            
            updateTimer();
        }

        // 실시간 카운트다운 및 구매 버튼 활성화 제어
        function updateTimer() {
            if (!serverOpenTime) return;
            const now = new Date().getTime();
            const distance = serverOpenTime - now;

            const banner = document.getElementById('timer-banner');
            const btn = document.getElementById('purchase-btn');

            if (distance <= 0) {
                banner.className = "mb-6 p-4 rounded-xl text-center font-semibold text-sm transition-all shadow-2xs bg-green-50 text-green-800 border border-green-200";
                banner.innerHTML = "🚀 <b>타임딜 오픈 진행 중!</b> 지금 바로 선착순 구매에 참여하세요.";
                
                btn.disabled = false;
                btn.className = "w-full bg-indigo-600 text-white font-semibold p-2.5 rounded-lg hover:bg-indigo-700 transition text-sm shadow-sm cursor-pointer";
                btn.innerText = "⚡ 빠르게 구매 신청하기";
            } else {
                const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                banner.className = "mb-6 p-4 rounded-xl text-center font-semibold text-sm transition-all shadow-2xs bg-amber-50 text-amber-900 border border-amber-200";
                banner.innerHTML = `⏳ 타임딜 오픈까지 남은 시간: <span class="font-mono font-bold text-base">${hours}시간 ${minutes}분 ${seconds}초</span>`;
                
                btn.disabled = true;
                btn.className = "w-full bg-gray-200 text-gray-500 font-semibold p-2.5 rounded-lg transition text-sm shadow-sm cursor-not-allowed";
                btn.innerText = "🔒 오픈 대기 중";
            }
        }

        async function submitPurchase(e) {
            e.preventDefault();
            const productId = document.getElementById('purchase-product-id').value;
            const name = document.getElementById('buyer-name').value.trim();
            const phone = document.getElementById('buyer-phone').value.trim();

            const nameRegex = /^[가-힣]{2,}$/;
            const phoneRegex = /^010\d{7,8}$/;
            const resultDiv = document.getElementById('purchase-result');

            if (!nameRegex.test(name)) {
                resultDiv.className = "mt-3 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs font-semibold";
                resultDiv.innerText = "❌ 입력 오류: 이름은 완성된 한글 2글자 이상 입력해주세요.";
                return;
            }

            if (!phoneRegex.test(phone)) {
                resultDiv.className = "mt-3 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs font-semibold";
                resultDiv.innerText = "❌ 입력 오류: 올바른 연락처 형식이 아닙니다. (예: 01012345678)";
                return;
            }

            const res = await fetch('/api/purchase', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({product_id: parseInt(productId), name, phone})
            });
            const result = await res.json();
            
            if (res.ok) {
                resultDiv.className = "mt-3 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-xs font-semibold";
                resultDiv.innerHTML = `🎉 [주문 성공 #${result.order.order_id}] ${result.message}`;
                loadStatus();
            } else {
                resultDiv.className = "mt-3 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs font-semibold";
                resultDiv.innerText = "❌ 실패/경계: " + result.error;
            }
        }

        async function searchOrders() {
            const name = document.getElementById('search-name').value;
            const res = await fetch(`/api/orders?name=${encodeURIComponent(name)}`);
            const data = await res.json();
            let resultDiv = document.getElementById('order-result');
            if (data.length === 0) {
                resultDiv.innerHTML = '<p class="text-gray-400 text-xs py-2 text-center">조회된 주문 내역이 없습니다.</p>';
                return;
            }
            let html = '';
            data.forEach(o => {
                html += `<div class="p-3 bg-white border border-gray-100 rounded-lg text-xs flex justify-between items-center shadow-2xs">
                    <div>
                        <span class="font-bold text-indigo-600">주문 #${o.order_id}</span> | <span class="text-gray-800">${o.product_name}</span>
                        <div class="text-gray-400 mt-0.5">${o.name} (${o.phone})</div>
                    </div>
                    <span class="bg-green-100 text-green-800 px-2 py-1 rounded font-semibold">${o.status}</span>
                </div>`;
            });
            resultDiv.innerHTML = html;
        }

        window.onload = () => {
            loadStatus();
            setInterval(updateTimer, 1000); // 1초마다 타이머 갱신
        };
    </script>
</body>
</html>
"""

# ==================== 2. 관리자 로그인 페이지 ====================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>관리자 인증</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 flex items-center justify-center h-screen">
    <div class="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <h2 class="text-xl font-bold mb-2 text-gray-900">🔒 관리자 인증</h2>
        <p class="text-gray-500 text-xs mb-6">시스템 관리자만 접근할 수 있는 구역입니다.</p>
        {% if error %}
        <div class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/admin/login" class="space-y-4">
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">관리자 아이디</label>
                <input type="text" name="username" required class="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
            </div>
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">비밀번호</label>
                <input type="password" name="password" required class="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
            </div>
            <button type="submit" class="w-full bg-gray-900 text-white p-2.5 rounded-lg hover:bg-black transition text-sm font-semibold">로그인</button>
        </form>
        <div class="mt-4 text-center">
            <a href="/" class="text-xs text-gray-400 hover:text-gray-600 transition">← 메인 화면으로 돌아가기</a>
        </div>
    </div>
</body>
</html>
"""

# ==================== 3. 관리자 대시보드 페이지 (오픈 시간 설정 기능 추가) ====================
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>관리자 대시보드</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-6">
    <div class="max-w-4xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-indigo-100">
        
        <div class="flex justify-between items-center mb-8 pb-4 border-b border-gray-100">
            <div class="flex items-center space-x-3">
                <div class="bg-indigo-600 text-white p-2.5 rounded-xl shadow-xs">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </div>
                <div>
                    <h1 class="text-2xl font-extrabold text-gray-900">관리자 대시보드</h1>
                    <p class="text-indigo-600 text-xs font-semibold mt-0.5">ADMINISTRATION CONTROL PANEL</p>
                </div>
            </div>
            <div class="space-x-2">
                <a href="/" class="bg-gray-100 text-gray-700 px-3.5 py-2 rounded-lg text-xs font-semibold hover:bg-gray-200 transition">사용자 홈</a>
                <a href="/admin/logout" class="bg-red-50 text-red-600 px-3.5 py-2 rounded-lg text-xs font-semibold hover:bg-red-100 transition">로그아웃</a>
            </div>
        </div>

        <!-- 타임딜 오픈 시간 설정 섹션 -->
        <div class="mb-8 p-6 bg-amber-50/50 border border-amber-200 rounded-2xl shadow-2xs">
            <h2 class="text-base font-bold text-amber-900 mb-2 flex items-center">
                <span class="mr-2">⏰</span> 타임딜 오픈 시간 설정
            </h2>
            <p class="text-xs text-amber-700 mb-4">현재 설정된 시간 이후에만 사용자들이 선착순 구매 신청을 할 수 있습니다.</p>
            <div class="flex space-x-2">
                <input type="datetime-local" id="open-time-input" class="p-2.5 bg-white border border-gray-200 rounded-lg text-sm flex-1 focus:ring-2 focus:ring-amber-500 focus:outline-none">
                <button onclick="updateOpenTime()" class="bg-amber-600 text-white px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-amber-700 transition shadow-xs">오픈 시간 변경</button>
                <button onclick="setOpenNow()" class="bg-green-600 text-white px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-green-700 transition shadow-xs">즉시 오픈하기</button>
            </div>
            <div id="time-msg" class="mt-2 text-xs font-semibold"></div>
        </div>

        <!-- 상품 등록/수정 섹션 -->
        <div class="mb-8 p-6 bg-indigo-50/50 border border-indigo-100 rounded-2xl shadow-2xs">
            <h2 class="text-base font-bold text-indigo-900 mb-3 flex items-center">
                <span class="mr-2">📦</span> 타임딜 상품 등록 및 수정
            </h2>
            <form id="product-form" onsubmit="saveProduct(event)" class="space-y-3">
                <input type="hidden" id="p-id" value="">
                <div>
                    <label class="block text-xs font-semibold text-gray-600 mb-1">상품명</label>
                    <input type="text" id="p-name" required class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">가격 (원)</label>
                        <input type="number" id="p-price" required class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">재고 수량</label>
                        <input type="number" id="p-stock" required class="w-full p-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                    </div>
                </div>
                <div class="flex space-x-2 pt-1">
                    <button type="submit" class="bg-indigo-600 text-white px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-indigo-700 transition shadow-xs">상품 저장/등록</button>
                    <button type="button" onclick="resetProductForm()" class="bg-white border border-gray-200 text-gray-700 px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-gray-50 transition">입력 초기화</button>
                </div>
            </form>
            <div id="product-msg" class="mt-2 text-xs font-semibold"></div>
        </div>

        <!-- 상품 현황 및 주문 목록 카드 그리드 -->
        <div class="grid grid-cols-2 gap-6">
            <div class="p-5 border border-gray-100 rounded-2xl bg-gray-50/50 shadow-2xs">
                <h2 class="text-sm font-bold text-gray-800 mb-3 flex items-center">
                    <span class="mr-2">📋</span> 등록된 상품 현황
                </h2>
                <div id="admin-product-list" class="space-y-2"></div>
            </div>
            <div class="p-5 border border-gray-100 rounded-2xl bg-gray-50/50 shadow-2xs">
                <h2 class="text-sm font-bold text-gray-800 mb-3 flex items-center">
                    <span class="mr-2">📑</span> 전체 주문자 목록
                </h2>
                <div id="admin-order-list" class="space-y-2"></div>
            </div>
        </div>
    </div>

    <script>
        async function loadAdminData() {
            // 상태(오픈 시간 및 상품) 로드
            const resStatus = await fetch('/api/status');
            const data = await resStatus.json();
            
            if(data.open_time) {
                // datetime-local 형식(YYYY-MM-DDTHH:mm)에 맞게 변환
                document.getElementById('open-time-input').value = data.open_time.slice(0, 16);
            }

            let prodHtml = '';
            for (let id in data.products) {
                let p = data.products[id];
                prodHtml += `<div class="p-3 bg-white border border-gray-100 rounded-xl flex justify-between items-center text-xs shadow-2xs">
                    <div>
                        <span class="font-bold text-gray-800 text-sm">${p.name}</span>
                        <div class="text-gray-400 mt-0.5">${p.price.toLocaleString()}원 | 잔여재고: <span class="text-indigo-600 font-semibold">${p.stock}개</span></div>
                    </div>
                    <button onclick="editProduct(${p.id}, '${p.name}', ${p.price}, ${p.stock})" class="bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded-lg font-semibold hover:bg-indigo-100 transition">수정</button>
                </div>`;
            }
            document.getElementById('admin-product-list').innerHTML = prodHtml;

            const resOrd = await fetch('/api/admin/orders');
            const orders = await resOrd.json();
            let ordHtml = '';
            if (orders.length === 0) {
                ordHtml = '<p class="text-gray-400 text-xs py-4 text-center">접수된 주문이 없습니다.</p>';
            } else {
                orders.forEach(o => {
                    ordHtml += `<div class="p-3 bg-white border border-gray-100 rounded-xl text-xs shadow-2xs">
                        <div class="flex justify-between items-center">
                            <span class="font-bold text-indigo-600">주문 #${o.order_id}</span>
                            <span class="bg-green-50 text-green-700 px-2 py-0.5 rounded font-semibold">${o.status}</span>
                        </div>
                        <div class="text-gray-800 font-medium mt-1">${o.product_name}</div>
                        <div class="text-gray-400 mt-0.5">구매자: ${o.name} (${o.phone})</div>
                    </div>`;
                });
            }
            document.getElementById('admin-order-list').innerHTML = ordHtml;
        }

        async function updateOpenTime() {
            const openTime = document.getElementById('open-time-input').value;
            const res = await fetch('/api/admin/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({open_time: openTime})
            });
            const result = await res.json();
            const msgDiv = document.getElementById('time-msg');
            if (res.ok) {
                msgDiv.className = "mt-2 text-xs font-semibold text-green-600";
                msgDiv.innerText = result.message;
            } else {
                msgDiv.className = "mt-2 text-xs font-semibold text-red-600";
                msgDiv.innerText = result.error;
            }
        }

        async function setOpenNow() {
            const now = new Date();
            now.setMinutes(now.getMinutes() - 1); // 현재보다 1분 전으로 설정하여 즉시 오픈
            const localIso = now.toISOString().slice(0, 16);
            document.getElementById('open-time-input').value = localIso;
            await updateOpenTime();
            document.getElementById('time-msg').className = "mt-2 text-xs font-semibold text-green-600";
            document.getElementById('time-msg').innerText = "⚡ 타임딜이 즉시 오픈되었습니다!";
            loadAdminData();
        }

        async function saveProduct(e) {
            e.preventDefault();
            const id = document.getElementById('p-id').value;
            const name = document.getElementById('p-name').value;
            const price = parseInt(document.getElementById('p-price').value);
            const stock = parseInt(document.getElementById('p-stock').value);

            const url = id ? `/api/admin/product/${id}` : '/api/admin/products';
            const method = id ? 'PUT' : 'POST';

            const res = await fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, price, stock})
            });
            const result = await res.json();
            const msgDiv = document.getElementById('product-msg');
            if (res.ok) {
                msgDiv.className = "mt-2 text-xs font-semibold text-green-600";
                msgDiv.innerText = result.message;
                resetProductForm();
                loadAdminData();
            } else {
                msgDiv.className = "mt-2 text-xs font-semibold text-red-600";
                msgDiv.innerText = result.error;
            }
        }

        function editProduct(id, name, price, stock) {
            document.getElementById('p-id').value = id;
            document.getElementById('p-name').value = name;
            document.getElementById('p-price').value = price;
            document.getElementById('p-stock').value = stock;
        }

        function resetProductForm() {
            document.getElementById('p-id').value = '';
            document.getElementById('product-form').reset();
        }

        window.onload = loadAdminData;
    </script>
</body>
</html>
"""

# ==================== 4. 플라스크 라우트 및 백엔드 오픈 시간 검증 로직 ====================


@app.route("/")
def index():
  return render_template_string(USER_TEMPLATE)


@app.route("/api/status", methods=["GET"])
def get_status():
  return jsonify({"open_time": sale_config["open_time"], "products": products})


@app.route("/api/products", methods=["GET"])
def get_products():
  return jsonify(products)


@app.route("/api/purchase", methods=["POST"])
def purchase():
  # 백엔드 서버 시간 기준 오픈 시간 검증 (사용자가 조작해도 서버에서 원천 차단)
  try:
    open_dt = datetime.fromisoformat(sale_config["open_time"])
    now_dt = datetime.now()
    if now_dt < open_dt:
      return jsonify({"error": "아직 타임딜 오픈 시간이 되지 않았습니다."}), 400
  except Exception:
    pass

  data = request.json
  p_id = data.get("product_id")
  name = data.get("name", "").strip()
  phone = data.get("phone", "").strip()

  name_pattern = r"^[가-힣]{2,}$"
  if not re.match(name_pattern, name):
    return jsonify(
        {"error": "이름은 완성된 한글 2글자 이상 입력해주세요."}
    ), 400

  phone_pattern = r"^010\d{7,8}$"
  if not re.match(phone_pattern, phone):
    return jsonify(
        {"error": "올바른 연락처 형식이 아닙니다. (예: 01012345678)"}
    ), 400

  if p_id not in products:
    return jsonify({"error": "존재하지 않는 상품입니다."}), 400

  product = products[p_id]
  if product["stock"] <= 0:
    return jsonify({"error": "재고가 모두 소진되었습니다. (품절)"}), 400

  product["stock"] -= 1
  order_id = len(orders) + 1
  new_order = {
      "order_id": order_id,
      "product_name": product["name"],
      "name": name,
      "phone": phone,
      "status": "주문 완료",
  }
  orders.append(new_order)
  return (
      jsonify({
          "message": f"'{product['name']}' 주문이 정상 접수되었습니다!",
          "order": new_order,
      }),
      200,
  )


@app.route("/api/orders", methods=["GET"])
def get_orders():
  name = request.args.get("name", "").strip()
  if not name:
    return jsonify([])
  matched = [o for o in orders if o["name"] == name]
  return jsonify(matched)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")
    if username == ADMIN_ID and password == ADMIN_PW:
      session["logged_in"] = True
      return redirect(url_for("admin_dashboard"))
    else:
      return render_template_string(
          LOGIN_TEMPLATE, error="아이디 또는 비밀번호가 올바르지 않습니다."
      )
  return render_template_string(LOGIN_TEMPLATE)


@app.route("/admin")
def admin_dashboard():
  if not session.get("logged_in"):
    return redirect(url_for("admin_login"))
  return render_template_string(ADMIN_TEMPLATE)


@app.route("/admin/logout")
def admin_logout():
  session.pop("logged_in", None)
  return redirect(url_for("admin_login"))


# 관리자 전용: 오픈 시간 설정 API
@app.route("/api/admin/config", methods=["POST"])
def admin_set_config():
  if not session.get("logged_in"):
    return jsonify({"error": "권한이 없습니다."}), 401
  data = request.json
  open_time = data.get("open_time")
  if not open_time:
    return jsonify({"error": "오픈 시간을 입력해주세요."}), 400

  sale_config["open_time"] = open_time
  return jsonify({"message": "타임딜 오픈 시간이 성공적으로 변경되었습니다."}), 200


@app.route("/api/admin/products", methods=["POST"])
def admin_add_product():
  if not session.get("logged_in"):
    return jsonify({"error": "권한이 없습니다."}), 401
  data = request.json
  name = data.get("name")
  price = data.get("price")
  stock = data.get("stock")
  if not name or price is None or stock is None:
    return jsonify({"error": "모든 항목을 입력해주세요."}), 400
  new_id = max(products.keys()) + 1 if products else 1
  products[new_id] = {"id": new_id, "name": name, "price": price, "stock": stock}
  return jsonify({"message": f"'{name}' 상품이 등록되었습니다."}), 201


@app.route("/api/admin/product/<int:p_id>", methods=["PUT"])
def admin_update_product(p_id):
  if not session.get("logged_in"):
    return jsonify({"error": "권한이 없습니다."}), 401
  if p_id not in products:
    return jsonify({"error": "존재하지 않는 상품입니다."}), 404
  data = request.json
  products[p_id]["name"] = data.get("name", products[p_id]["name"])
  products[p_id]["price"] = data.get("price", products[p_id]["price"])
  products[p_id]["stock"] = data.get("stock", products[p_id]["stock"])
  return jsonify({"message": "상품 정보가 수정되었습니다."}), 200


@app.route("/api/admin/orders", methods=["GET"])
def admin_get_orders():
  if not session.get("logged_in"):
    return jsonify({"error": "권한이 없습니다."}), 401
  return jsonify(orders)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)