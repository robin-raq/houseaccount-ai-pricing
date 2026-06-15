# Rate-limit the unauthenticated demo playground so anonymous traffic can't drain the
# OpenAI key or hammer the model service. The bearer-protected contract is not throttled.
Rack::Attack.cache.store = ActiveSupport::Cache::MemoryStore.new

# Each demo POST creates a real staging booking + an OpenAI call, so keep the ceiling low.
Rack::Attack.throttle("demo/ip", limit: 8, period: 60) do |request|
  request.ip if request.post? && request.path.start_with?("/demo")
end

Rack::Attack.throttled_responder = lambda do |_request|
  body = { error: "Rate limit exceeded", retry_after: 60 }.to_json
  [ 429, { "Content-Type" => "application/json", "Retry-After" => "60" }, [ body ] ]
end
