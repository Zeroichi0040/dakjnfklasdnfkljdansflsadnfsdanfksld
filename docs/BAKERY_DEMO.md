# Demonstration checklist

Run setup, start the server, and use the locally opened site. This is a demo store;
no payment ever transfers money. Create a separate administrator using
`python manage.py create-admin`; do not use a shared password. Products and prices
below refer to a fresh sample catalogue; existing edits are preserved by seeding.

1. **Register a customer** at `/auth/register`. Use a name, valid email and password
   of at least 12 characters. Confirm the personalized `/app` dashboard appears.
2. **Sign in** after signing out. Profile settings display the same account details.
3. **Browse** `/products`; filter Bread, search Pandesal and sort by price. Open a
   product detail to see stock, allergens and related products.
4. **Add to basket** two Classic Pandesal packs (₱48 each initially). Cart total is
   ₱96; update quantities and remove/re-add a line. Anonymous baskets survive login.
5. **Check out** with pickup name and phone. Choose GCash or card simulation and
   Successful payment. Never enter financial credentials. Receipt shows pending
   order and paid simulated payment, with the server-calculated total.
6. **View history** at `/orders` and recent orders at `/app`. Open the receipt. A
   second customer must not be able to open the first customer's order URL.
7. **Sign in as administrator** using the account created from the owner console.
8. **View the order** under `/admin/bakery/orders`; filter Pending and open details.
9. **Update its status** pending → preparing → ready → completed. Try an invalid
   jump through a forged/stale form to observe server rejection. Completed is final.
10. **Edit inventory** under `/admin/bakery/products`: change stock/price, create a
    product, deactivate it and verify public exclusion. Negative stock is rejected.
    A stale tab opened before checkout cannot overwrite the new inventory version.
11. **View finances** at `/admin/bakery`: completed paid sales, completed count,
    average order value, bestseller units and date bars reflect the receipt.
12. **Demonstrate failed payment** with another basket. Choose Declined or
    Insufficient balance. Receipt shows cancelled order and failed payment; stock
    is restored and sales totals do not increase. Payment Cancellation has its own
    cancelled payment status. Do not retry a failed order by changing its status;
    make a new basket/order instead.
13. **Demonstrate no stock** with the seeded Cinnamon Morning Roll. Purchasing is
    disabled. A forged add/checkout beyond available stock is also rejected server-side.
14. **Demonstrate customer cancellation** of another pending successful order.
    Payment becomes refunded (simulation), stock returns once. Refreshing/reposting
    does not return it twice. Cancellation is unavailable to the customer after preparation.
15. **Demonstrate cash pickup**: choose Cash on pickup and Successful payment.
    Receipt correctly says unpaid. Admin moves it to ready, records simulated cash
    collection, then completes it. It contributes to completed sales only now.
16. **Send an inquiry** through Contact; open existing administrator Messages and
    resolve it. Notes, uploaded files, page publishing and account administration
    remain reachable in the sidebar.
17. **Check persistence**: stop/restart the server; customer orders, stock changes
    and published content remain. A new browser has an empty cart, not empty history.

Run `python -m pytest -q` for repeatable isolated edge-case and security checks.
The browser demo does not replace database concurrency tests.
