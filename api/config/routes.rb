Rails.application.routes.draw do
  # External Appendix A contract: POST /pricing-estimate. Any other verb on the
  # same path returns the contract's 405 JSON body rather than a 404.
  resource :pricing_estimate, only: :create, path: "pricing-estimate"
  match "pricing-estimate", to: "errors#method_not_allowed",
        via: %i[get put patch delete], format: false

  # Liveness probe for the platform.
  get "up" => "rails/health#show", as: :rails_health_check
end
