# Memorabiliacs

Memorabiliacs is a web application built with Streamlit that allows users to document and manage their memorabilia collections online. Users can create personalized collections, search for items from various sources (such as movies, LEGO sets, Pokémon cards, and custom items via UPC codes), and organize their collectibles with notes and quantities.

## Features

- **User Authentication**: Secure login and user management using Firebase.
- **Collection Management**: Create, edit, rename, and hide collections of different types (e.g., Movies, LEGO, Pokémon, Custom).
- **Search Functionality**: Search for collectibles from our database utilizing algolia:
  - Movies and TV shows
  - LEGO sets/minifigs
  - Pokémon and many other trading cards
  - UPC/EAN/ISBN barcode lookup for anything under the sun!
- **Barcode Scanning**: Upload images or use camera input to scan barcodes for custom items.
- **Multi-language Support**: Available in English, Spanish, French, Klingon, and Simplified Chinese.
- **Customizable Themes**: Personalize the app's appearance with background images, colors, and sounds.
- **Settings**: Configure user preferences, including language and theme settings.
- **Data Storage**: Uses Google Firestore for secure cloud storage of user data and collections.

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Memorabiliacs
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables or Streamlit secrets for API keys (Firebase, TMDb, Algolia, etc.). Refer to Streamlit documentation for managing secrets.

4. Run the application:
   ```
   streamlit run memorabiliacs.py
   ```

## Usage

1. **Login**: Start by logging in with your credentials.
2. **Home Page**: View and manage your collections.
3. **Add Collections**: Create new collections by specifying a name and type.
4. **Search Items**: Use the search page to find items from supported sources and add them to your collections.
5. **Settings**: Customize your experience in the settings page.

## Project Structure

- `memorabiliacs.py`: Main entry point for the Streamlit app.
- `pages/`: Contains page modules for different app sections (home, login, search, settings, etc.).
- `BackendMethods/`: Backend functions for authentication, database operations, and API integrations.
- `locale/`: Translation files for multi-language support.
- `sounds/`: Audio files for user feedback.
- `thumbnails/`: Image thumbnails for collections.

## Dependencies

See `requirements.txt` for a full list of dependencies, including Streamlit, Firebase Admin, Google Cloud libraries, and various API clients.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

