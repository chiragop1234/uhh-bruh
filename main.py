from flask import Flask, render_template_string, request, jsonify
import stripe
import threading
import time
import os
import sys
import urllib2
import json
import platform
import subprocess

app = Flask(__name__)

# Replace with your actual Stripe secret key
stripe.api_key = "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"

# Replace with your actual Stripe publishable key
publishable_key = "pk_live_51PQ2NsIRVZuMm36D3qfRK71bc05tbkpDsau16aIvaUrohjcIovFhHK9BBQGWsdKEq4jQvuSyE4uz4SORxovI61ow00xwc4sb95"

def validate_stripe_keys():
    error_message = None

    # Check if the secret key is set
    if not stripe.api_key or stripe.api_key == "YOUR_STRIPE_SECRET_KEY":
        error_message = "Error: Stripe secret key (sk) is not set correctly."

    # Check if the publishable key is set
    elif not publishable_key or publishable_key == "YOUR_STRIPE_PUBLISHABLE_KEY":
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

def start_ngrok():
    try:
        # Extract ngrok from the tar.gz file if not already extracted
        tar_file = 'ngrok-v3-stable-linux-amd64.tgz'
        ngrok_executable = 'ngrok'  # For Linux and macOS
        if not os.path.exists(ngrok_executable):
            if os.path.exists(tar_file):
                print("Extracting ngrok from tar.gz file...")
                import tarfile
                with tarfile.open(tar_file, 'r:gz') as tar:
                    tar.extractall()
                os.chmod(ngrok_executable, 0o755)
                print("ngrok extracted and made executable.")
            else:
                print("Error: ngrok tar.gz file not found.")
                sys.exit(1)
        else:
            print("ngrok executable already exists.")

        ngrok_command = './ngrok'

        # Set your ngrok authtoken
        ngrok_authtoken = "2oZhLAwMehKLxmasAfn8DbDiz5x_5KnGwrgC1YD7reiK7p6HJ"  # Replace with your actual ngrok authtoken

        if not ngrok_authtoken or ngrok_authtoken == "YOUR_NGROK_AUTHTOKEN":
            print("Error: ngrok authtoken is not set.")
            sys.exit(1)

        # Authenticate ngrok with your authtoken
        cmd_auth = [ngrok_command, 'config', 'add-authtoken', ngrok_authtoken]
        subprocess.check_call(cmd_auth)

        # Start ngrok
        cmd = [ngrok_command, 'http', '50050']
        subprocess.Popen(cmd)
        # ngrok runs in the background
    except Exception as e:
        print("Error starting ngrok:", e)
        sys.exit(1)

def get_tunnel_url():
    # Use ngrok's API to get the public URL
    url = "http://127.0.0.1:4040/api/tunnels"
    max_retries = 15
    tunnel_url = None
    for i in range(max_retries):
        try:
            response = urllib2.urlopen(url)
            data = json.load(response)
            for tunnel in data['tunnels']:
                if tunnel['proto'] == 'https':
                    tunnel_url = tunnel['public_url']
                    return tunnel_url
            # If not found, wait and retry
            time.sleep(1)
        except Exception as e:
            time.sleep(1)
    print("Failed to get ngrok tunnel URL.")
    sys.exit(1)

@app.route('/', methods=['GET'])
def index():
    error_message = validate_stripe_keys()
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
        </head>
        <body>
            <h1>Stripe Payment Form</h1>
            <form id="payment-form">
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
            <div id="payment-message"></div>

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
                        // Send the token and other form data to the server via AJAX
                        var formData = new FormData();
                        formData.append('stripeToken', result.token.id);
                        formData.append('name', document.getElementById('name').value);
                        formData.append('email', document.getElementById('email').value);

                        fetch('/', {
                            method: 'POST',
                            body: formData
                        })
                        .then(function(response) {
                            return response.json();
                        })
                        .then(function(data) {
                            var paymentMessage = document.getElementById('payment-message');
                            if (data.success) {
                                paymentMessage.textContent = data.message;
                                paymentMessage.style.color = 'green';
                                console.log("Payment successful:", data.message);
                            } else {
                                paymentMessage.textContent = data.error;
                                paymentMessage.style.color = 'red';
                                console.error("Payment error:", data.error);
                            }
                        })
                        .catch(function(error) {
                            console.error("Fetch error:", error);
                        });
                    }
                });
            }

            document.getElementById('payment-form').addEventListener('submit', handleForm);
            </script>
        </body>
        </html>
        ''', publishable_key=publishable_key)

@app.route('/', methods=['POST'])
def process_payment():
    error_message = validate_stripe_keys()
    if error_message:
        return jsonify({'success': False, 'error': error_message}), 400

    name = request.form.get('name')
    email = request.form.get('email')
    token = request.form.get('stripeToken')

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
        success_message = 'Thank you for your payment, {}!'.format(name)
        return jsonify({'success': True, 'message': success_message}), 200

    except stripe.error.CardError as e:
        # Card was declined
        err = e.json_body.get('error', {})
        error_message = err.get('message')
        return jsonify({'success': False, 'error': error_message}), 400

    except stripe.error.RateLimitError:
        error_message = 'Rate limit error.'
        return jsonify({'success': False, 'error': error_message}), 429

    except stripe.error.InvalidRequestError:
        error_message = 'Invalid parameters.'
        return jsonify({'success': False, 'error': error_message}), 400

    except stripe.error.AuthenticationError:
        error_message = 'Authentication error.'
        return jsonify({'success': False, 'error': error_message}), 401

    except stripe.error.APIConnectionError:
        error_message = 'Network error.'
        return jsonify({'success': False, 'error': error_message}), 503

    except stripe.error.StripeError:
        error_message = 'Payment processing error. Please try again.'
        return jsonify({'success': False, 'error': error_message}), 500

    except Exception as e:
        error_message = 'An error occurred: {}'.format(str(e))
        return jsonify({'success': False, 'error': error_message}), 500

if __name__ == '__main__':
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()

    # Wait for ngrok to start and get the tunnel URL
    time.sleep(3)
    tunnel_url = get_tunnel_url()
    print("ngrok tunnel URL:", tunnel_url)

    # Start the Flask app
    app.run(host='127.0.0.1', port=50050, debug=True)
