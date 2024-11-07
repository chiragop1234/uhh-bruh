from flask import Flask, render_template_string, request
import stripe

app = Flask(__name__)

# Replace with your actual Stripe secret key
stripe.api_key = "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"

# Replace with your actual Stripe publishable key
publishable_key = "pk_live_51PQ2NsIRVZuMm36D3qfRK71bc05tbkpDsau16aIvaUrohjcIovFhHK9BBQGWsdKEq4jQvuSyE4uz4SORxovI61ow00xwc4sb95"

def validate_stripe_keys():
    error_message = None

    # Check if the secret key is set
    if not stripe.api_key or stripe.api_key == "YOUR_SECRET_KEY":
        error_message = "Error: Stripe secret key (sk) is not set correctly."

    # Check if the publishable key is set
    elif not publishable_key or publishable_key == "YOUR_PUBLISHABLE_KEY":
        error_message = "Error: Stripe publishable key (pk) is not set correctly."

    else:
        try:
            # Attempt to retrieve Stripe account to verify the secret key
            stripe.Account.retrieve()
        except stripe.error.AuthenticationError:
            error_message = "Error: Invalid Stripe secret key (sk). Please check your configuration."
        except Exception as e:
            error_message = "Error: An error occurred while validating the Stripe keys: {}".format(str(e))

    return error_message

@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = validate_stripe_keys()
    payment_message = ''
    if error_message:
        # Render an error page if keys are invalid and log to console
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <script>
                    console.error("{{ error_message }}");
                </script>
            </head>
            <body><h1>{{ error_message }}</h1></body>
            </html>
            ''', error_message=error_message)
    else:
        if request.method == 'POST':
            # Handle payment processing
            name = request.form['name']
            email = request.form['email']
            token = request.form['stripeToken']

            try:
                # Create customer
                customer = stripe.Customer.create(
                    email=email,
                    name=name,
                    source=token
                )

                # Create charge
                charge = stripe.Charge.create(
                    customer=customer.id,
                    amount=50,  # Amount in cents
                    currency='usd',
                    description='Flask Charge'
                )
                payment_message = 'Thank you for your payment, {}!'.format(name)
            except stripe.error.CardError as e:
                # Card was declined
                err = e.json_body.get('error', {})
                payment_message = err.get('message')
            except stripe.error.RateLimitError:
                payment_message = 'Rate limit error.'
            except stripe.error.InvalidRequestError:
                payment_message = 'Invalid parameters.'
            except stripe.error.AuthenticationError:
                payment_message = 'Authentication error.'
            except stripe.error.APIConnectionError:
                payment_message = 'Network error.'
            except stripe.error.StripeError:
                payment_message = 'Payment processing error. Please try again.'
            except Exception as e:
                payment_message = 'An error occurred: {}'.format(str(e))

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stripe Payment</title>
            <style>
                /* CSS styles */
                .StripeElement {
                    box-sizing: border-box;
                    height: 40px;
                    padding: 10px 12px;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    background-color: white;
                    box-shadow: 0 1px 3px 0 #e6ebf1;
                    transition: box-shadow 150ms ease;
                }
                .StripeElement--focus {
                    box-shadow: 0 1px 3px 0 #cfd7df;
                }
                .StripeElement--invalid {
                    border-color: #fa755a;
                }
                body {
                    font-family: Arial, sans-serif;
                    margin: 50px;
                }
                form div {
                    margin-bottom: 15px;
                }
                label {
                    display: block;
                    margin-bottom: 5px;
                }
                button {
                    background-color: #6772e5;
                    color: white;
                    padding: 8px 12px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                #card-errors {
                    color: #fa755a;
                }
                #payment-message {
                    color: green;
                    margin-top: 20px;
                }
            </style>
            <!-- Load Stripe.js -->
            <script src="https://js.stripe.com/v3/"></script>
            <script>
            // Initialize Stripe with the publishable key
            var stripe = Stripe('{{ publishable_key }}');

            // Create an instance of Elements
            var elements = stripe.elements();

            // Custom styling
            var style = {
                base: {
                    fontSize: '16px',
                    color: '#32325d',
                },
            };

            // Create an instance of the card Element
            var card = elements.create('card', {style: style});

            // Add card Element to the DOM
            document.addEventListener("DOMContentLoaded", function() {
                card.mount('#card-element');
            });

            // Handle real-time validation errors
            card.on('change', function(event) {
                var displayError = document.getElementById('card-errors');
                if (event.error) {
                    displayError.textContent = event.error.message;
                } else {
                    displayError.textContent = '';
                }
            });

            // Handle form submission
            function handleForm(event) {
                event.preventDefault();

                stripe.createToken(card).then(function(result) {
                    if (result.error) {
                        // Display error in card-errors div
                        var errorElement = document.getElementById('card-errors');
                        errorElement.textContent = result.error.message;
                        console.error("Stripe createToken error:", result.error.message);
                    } else {
                        // Insert the token ID into the form and submit
                        var form = document.getElementById('payment-form');
                        var hiddenInput = document.createElement('input');
                        hiddenInput.setAttribute('type', 'hidden');
                        hiddenInput.setAttribute('name', 'stripeToken');
                        hiddenInput.setAttribute('value', result.token.id);
                        form.appendChild(hiddenInput);

                        form.submit();
                    }
                });
            }
            </script>
        </head>
        <body>
            <h1>Stripe Payment Form</h1>
            <form id="payment-form" method="POST" onsubmit="handleForm(event);">
                <div>
                    <label for="name">Name</label>
                    <input type="text" name="name" id="name" required/>
                </div>
                <div>
                    <label for="email">Email</label>
                    <input type="email" name="email" id="email" required/>
                </div>
                <div>
                    <label for="card-element">Credit or Debit Card</label>
                    <div id="card-element" class="StripeElement">
                    <!-- Stripe Element will be inserted here -->
                    </div>
                </div>
                <!-- Display form errors -->
                <div id="card-errors" role="alert"></div>
                <button type="submit">Submit Payment</button>
            </form>
            <!-- Payment message -->
            {% if payment_message %}
                <div id="payment-message">{{ payment_message }}</div>
                <script>
                    console.log("Payment Message: {{ payment_message }}");
                </script>
            {% endif %}
        </body>
        </html>
        ''', publishable_key=publishable_key, payment_message=payment_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=50302, debug=True)
