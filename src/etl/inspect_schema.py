from src.etl.loader import load_all_core_data


def main():
    data = load_all_core_data()

    print("\n" + "=" * 70)
    print("BLUESTOCK CORE DATASET SCHEMA")
    print("=" * 70)

    for name, df in data.items():
        print(f"\n{name.upper()}")
        print("-" * 70)
        print(f"Rows    : {len(df)}")
        print(f"Columns : {len(df.columns)}")

        for column in df.columns:
            print(f"  - {column}")


if __name__ == "__main__":
    main()