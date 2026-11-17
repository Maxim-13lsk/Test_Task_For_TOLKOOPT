import asyncio
import unittest
from decimal import Decimal as D

from starter import recommend_price, sample_fetch_offers


def offer(seller, price, days):
    return {"seller": seller, "price": D(price), "delivery_days": days}


def source(offers, status="success"):
    async def fetch():
        return {"status": status, "offers": offers}
    return fetch


def run(fetch, current="1000.00", minimum="1.00", **kw):
    return asyncio.run(recommend_price(fetch, D(current), D(minimum), **kw))


class RecommendPriceTest(unittest.TestCase):
    def test_normal_calculation(self):
        res = asyncio.run(recommend_price(
            sample_fetch_offers, D("4900.00"), D("4500.00")))
        self.assertEqual(res["price"], D("4728.00"))
        self.assertEqual(res["decision"], "APPLY")

    def test_timeout_returns_hold_with_current_price(self):
        async def hanging():
            await asyncio.sleep(10)

        res = run(hanging, current="1234.56", timeout_s=0.01)
        self.assertEqual(res["decision"], "HOLD")
        self.assertEqual(res["price"], D("1234.56"))

    def test_source_exception_and_non_success_status_hold(self):
        async def broken():
            raise RuntimeError("boom")

        self.assertEqual(run(broken)["decision"], "HOLD")
        for status in ("partial", "error"):
            res = run(source([offer("A", "900.00", 1)], status=status))
            self.assertEqual(res["decision"], "HOLD")
            self.assertEqual(res["price"], D("1000.00"))

    def test_filtering_own_shop_and_delivery(self):
        offers = [
            offer("MyShop", "10.00", 1),
            offer("MYSHOP", "11.00", 1),
            offer("NoInfo", "12.00", None),
            offer("Slow", "13.00", 7),
            offer("Edge", "900.00", 6),
        ]
        res = run(source(offers))
        self.assertEqual(res["price"], D("886.50"))
        self.assertEqual(res["decision"], "APPLY")

    def test_no_suitable_offers_hold_even_below_min_price(self):
        res = run(source([offer("Slow", "500.00", 9)]),
                  current="800.00", minimum="1000.00")
        self.assertEqual(res["decision"], "HOLD")
        self.assertEqual(res["price"], D("800.00"))

    def test_rounds_down_to_kopeck(self):
        res = run(source([offer("A", "100.01", 1)]), current="100.00")
        self.assertEqual(res["price"], D("98.50"))

    def test_min_price_floor(self):
        res = run(source([offer("A", "1000.00", 1)]), minimum="990.00")
        self.assertEqual(res["price"], D("990.00"))
        self.assertEqual(res["decision"], "APPLY")

    def test_exactly_30_percent_applies_more_goes_to_review(self):
        cheap = source([offer("A", "100.00", 1)])
        # рекомендация = min_price: ровно -30% и чуть больше
        self.assertEqual(run(cheap, minimum="700.00")["decision"], "APPLY")
        self.assertEqual(run(cheap, minimum="699.99")["decision"], "REVIEW")
        # ровно +30% и чуть больше
        dear = source([offer("A", "1000.00", 1)])  # 985.00 < min_price -> берётся min_price
        self.assertEqual(run(dear, minimum="1300.00")["decision"], "APPLY")
        res = run(dear, minimum="1300.01")
        self.assertEqual(res["decision"], "REVIEW")
        self.assertEqual(res["price"], D("1300.01"))


if __name__ == "__main__":
    unittest.main()
