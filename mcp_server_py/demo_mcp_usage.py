
import sys
import os

# Ensure we can import server_sdk
sys.path.append("/mcp_server_py")

try:
    import server_sdk
    
    # 1. Initialize
    print("Initializing config...")
    server_sdk.reset_config_builder()
    builder = server_sdk.get_config_builder()

    # 2. Add Person Column "Name"
    print("Adding 'Name' column...")
    builder.add_column(
        server_sdk.SamplerColumnConfig(
            name="Name",
            sampler_type=server_sdk.SamplerType.PERSON,
            params=server_sdk.PersonSamplerParams(age_range=[18, 70])
        )
    )

    # 3. Preview Data
    print("Previewing 5 records...")
    client = server_sdk.get_client()
    preview = client.preview(builder, num_records=5)

    if preview and hasattr(preview, 'dataset') and preview.dataset is not None:
        print("\n--- Generated Data ---")
        print(preview.dataset.head(5).to_string(index=False))
        print("----------------------\n")
    else:
        print(f"Preview result: {preview}")

except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    import traceback
    traceback.print_exc()
