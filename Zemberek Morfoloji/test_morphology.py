from py4j.java_gateway import JavaGateway

gateway = JavaGateway()
zemberek = gateway.entry_point

test_words = ["koyun"]

for word in test_words:
    results = zemberek.getAnalysisResults(word)
    print(f"\n{word}:")
    for r in results:
        print(f"  {r}")

gateway.close()
