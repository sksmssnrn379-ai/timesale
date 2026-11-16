from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# 메모리 기반 가상 데이터베이스 (타임딜 상품 및 주문 내역)
products = {
    1: {
        "id": 1,
        "name": "리미티드 에디션 스니커즈",
        "price": 150000,
        "stock": 3,
    },  # 경계 테스트를 위해 재고를 3개로 설정
    2: {"id": 2, "name": "한정판 후드티 굿즈", "price": 69000, "stock": 5},
}

orders = []  # 주문 내역 저장 리스트

# HTML 프론트엔드 화면 (사용자 기능 3가지)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>한정판 타임세일 선착순 구매 서비스</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-6">
    <div class="max-w-3xl mx-auto bg-white p-6 rounded-lg shadow-md">
        <h1 class="text-2xl font-bold mb-2 text-indigo-600">⚡ 한정판 굿즈 타임세일 서비스</h1>
        <p class="text-gray-600 mb-6">사용자 기능 검증을 위한 선착순 구매 시스템입니다.</p>

        <!-- 기능 1: 타임딜 상품 및 잔여 재고 조회 -->
        <div class="mb-8 p-4 border rounded bg-gray-50">
            <h2 class="text-lg font-semibold mb-2 text-indigo-700">📌 기능 1: 타임딜 상품 및 잔여 재고 조회</h2>
            <p class="text-sm text-gray-500 mb-3">현재 진행 중인 한정판 상품의 실시간 잔여 수량을 확인할 수 있습니다.</p>
            <button onclick="loadProducts()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 text-sm">상품 목록 새로고침</button>
            <div id="product-list" class="mt-4 grid grid-cols-2 gap-4"></div>
        </div>

        <!-- 기능 2: 선착순 굿즈 구매 신청 (트래픽 집중 기능) -->
        <div class="mb-8 p-4 border rounded bg-gray-50">
            <h2 class="text-lg font-semibold mb-2 text-indigo-700">📌 기능 2: 선착순 굿즈 구매 신청</h2>
            <p class="text-sm text-gray-500 mb-3">정각에 접속해 선착순으로 구매를 신청하고 재고가 차감되는지 확인합니다.</p>
            <form id="purchase-form" onsubmit="submitPurchase(event)" class="space-y-3">
                <div>
                    <label class="block text-sm font-medium">상품 선택</label>
                    <select id="purchase-product-id" class="w-full p-2 border rounded"></select>
                </div>
                <div>
                    <label class="block text-sm font-medium">구매자 이름</label>
                    <input type="text" id="buyer-name" required class="w-full p-2 border rounded" placeholder="예: 홍길동">
                </div>
                <div>
                    <label class="block text-sm font-medium">연락처</label>
                    <input type="text" id="buyer-phone" required class="w-full p-2 border rounded" placeholder="010-0000-0000">
                </div>
                <button type="submit" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 text-sm">구매 신청하기</button>
            </form>
            <div id="purchase-result" class="mt-3 font-semibold text-sm"></div>
        </div>

        <!-- 기능 3: 주문 접수 내역 조회 -->
        <div class="p-4 border rounded bg-gray-50">
            <h2 class="text-lg font-semibold mb-2 text-indigo-700">📌 기능 3: 주문 접수 내역 조회</h2>
            <p class="text-sm text-gray-500 mb-3">본인의 이름으로 정상 접수되었는지 주문 내역을 조회합니다.</p>
            <div class="flex space-x-2 mb-3">
                <input type="text" id="search-name" placeholder="주문자 이름 입력 (예: 홍길동)" class="p-2 border rounded flex-1 text-sm">
                <button onclick="searchOrders()" class="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 text-sm">내역 조회</button>
            </div>
            <div id="order-result" class="space-y-2"></div>
        </div>
    </div>

    <script>
        async function loadProducts() {
            const res = await fetch('/api/products');
            const data = await res.json();
            let html = '';
            let selectHtml = '';
            for (let id in data) {
                let p = data[id];
                html += `<div class="p-3 bg-white border rounded shadow-sm">
                    <p class="font-bold">${p.name}</p>
                    <p class="text-sm text-gray-500">가격: ${p.price.toLocaleString()}원</p>
                    <p class="text-sm font-semibold text-indigo-600">잔여 재고: ${p.stock}개</p>
                </div>`;
                selectHtml += `<option value="${p.id}">${p.name} (잔여: ${p.stock}개)</option>`;
            }
            document.getElementById('product-list').innerHTML = html;
            document.getElementById('purchase-product-id').innerHTML = selectHtml;
        }

        async function submitPurchase(e) {
            e.preventDefault();
            const productId = document.getElementById('purchase-product-id').value;
            const name = document.getElementById('buyer-name').value;
            const phone = document.getElementById('buyer-phone').value;

            const res = await fetch('/api/purchase', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({product_id: parseInt(productId), name, phone})
            });
            const result = await res.json();
            const resultDiv = document.getElementById('purchase-result');
            if (res.ok) {
                resultDiv.className = "mt-3 font-semibold text-sm text-green-600";
                resultDiv.innerText = "성공: " + result.message;
                loadProducts();
            } else {
                resultDiv.className = "mt-3 font-semibold text-sm text-red-600";
                resultDiv.innerText = "실패/경계: " + result.error;
            }
        }

        async function searchOrders() {
            const name = document.getElementById('search-name').value;
            const res = await fetch(`/api/orders?name=${encodeURIComponent(name)}`);
            const data = await res.json();
            let resultDiv = document.getElementById('order-result');
            if (data.length === 0) {
                resultDiv.innerHTML = '<p class="text-gray-500 text-sm">조회된 주문 내역이 없습니다.</p>';
                return;
            }
            let html = '';
            data.forEach(o => {
                html += `<div class="p-2 bg-white border rounded text-sm">
                    주문번호: #${o.order_id} | 상품: ${o.product_name} | 구매자: ${o.name} (${o.phone}) | 상태: <span class="text-green-600 font-bold">${o.status}</span>
                </div>`;
            });
            resultDiv.innerHTML = html;
        }

        window.onload = loadProducts;
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/api/products", methods=["GET"])
def get_products():
  return jsonify(products)


@app.route("/api/purchase", methods=["POST"])
def purchase():
  data = request.json
  p_id = data.get("product_id")
  name = data.get("name")
  phone = data.get("phone")

  if p_id not in products:
    return jsonify({"error": "존재하지 않는 상품입니다."}), 400

  product = products[p_id]

  # 경계/실패 시험: 재고 부족 시 차단
  if product["stock"] <= 0:
    return jsonify({"error": "재고가 모두 소진되었습니다. (품절)"}), 400

  # 정상 시험: 재고 차감 및 주문 생성
  product["stock"] -= 1
  order_id = len(orders) + 1
  new_order = {
      "order_id": order_id,
      "product_name": product["name"],
      "name": name,
      "phone": phone,
      "status": "주문 완료 (정상 접수)",
  }
  orders.append(new_order)
  return (
      jsonify({
          "message": f"'{product['name']}' 주문이 성공적으로 접수되었습니다!",
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


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)