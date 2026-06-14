Rails.application.routes.draw do
  # External Appendix A contract: POST /pricing-estimate. Any other verb on the
  # same path returns the contract's 405 JSON body rather than a 404.
  resource :pricing_estimate, only: :create, path: "pricing-estimate"
  match "pricing-estimate", to: "errors#method_not_allowed",
        via: %i[get put patch delete], format: false

  # Public demo playground (no bearer; the secret stays server-side). The UI calls
  # #create to price and #index for the recent-request log shown on the API screen.
  namespace :demo do
    resources :estimates, only: %i[create index]
    resource :model, only: :show
  end

  # Liveness probe for the platform.
  get "up" => "rails/health#show", as: :rails_health_check

  # Serve the single-page demo UI from public/index.html at the root.
  root to: redirect("/index.html")
end
