export type ModelOption = {
  provider: string;
  model: string;
  display_name: string;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_json: boolean;
  input_price_per_1m: string | null;
  output_price_per_1m: string | null;
};
