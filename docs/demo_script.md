# 3–5 Minute Demonstration Script

1. **Introduce the problem (20–30 seconds).** Explain that the fictional retailer has product, delivery, warranty and return documents. The assistant retrieves evidence before generating answers.
2. **Show a successful answer (45 seconds).** Ask: “What is the delivery fee outside Dhaka?” Show the answer and expand Sources used / Retrieved passages.
3. **Show a multi-fact answer (45 seconds).** Ask: “What is the price and warranty of the Nova A1 Smartphone?” Verify the answer against the product and warranty documents.
4. **Show an unknown question (45 seconds).** Ask: “Does the EchoBuds Lite support wireless charging?” The knowledge base does not specify this; demonstrate the fallback rather than a fabricated answer.
5. **Show ambiguity handling (20 seconds).** Ask: “How much does it cost?” The app should ask which product or service.
6. **Show evaluation evidence (45–60 seconds).** Open the evaluation CSV and summary JSON. Explain retrieval hit rate, reference-fact coverage, manual relevance/grounding review and measured latency. Mention actual failures and the tested improvement.
7. **Close (15 seconds).** State current limitations and the next steps for a real deployment.

Only record the final demonstration after running the app and evaluation successfully. Do not present placeholder metrics as results.
