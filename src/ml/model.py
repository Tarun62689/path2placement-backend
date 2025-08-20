import sys
import json

def predict(features):
    # Dummy example model (replace with ML code)
    # Just return the sum of features
    return {"prediction": sum(features)}

if __name__ == "__main__":
    try:
        # Read input from Node
        input_data = sys.stdin.read()
        data = json.loads(input_data)

        features = data.get("features", [])
        result = predict(features)

        # ✅ Always print JSON for Node to parse
        print(json.dumps(result))
        sys.stdout.flush()
    except Exception as e:
        # Print error as JSON so Node can handle it
        print(json.dumps({"error": str(e)}))
        sys.stdout.flush()
