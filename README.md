# Internal Link Finding Tool

This project is designed to help find internal linking opportunities within a website.

## Setup

1. Clone the repository:
   ```sh
   git clone https://github.com/naveen3830/internal_link_finding.git
   cd internal_link_finding
   ```

2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

4. Run the Streamlit application:
   ```sh
   streamlit run app.py
   ```

## Usage

- Upload your source URLs and keyword-target URL pairs.
- Process the data to find internal linking opportunities.
- Download the results as a CSV file.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a pull request.

## License

This project is licensed under the MIT License.