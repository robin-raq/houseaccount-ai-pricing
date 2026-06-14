# Boot-time enforcement (Appendix A): the app must throw on cold start if the bearer
# secret is unset, rather than silently booting and rejecting every request. Skipped
# in test/development so the suite and local boot don't require the production secret.
if Rails.env.production? && ENV["GAUNTLET_PRICING_SECRET"].to_s.strip.empty?
  raise "GAUNTLET_PRICING_SECRET is unset — refusing to boot the pricing API."
end
