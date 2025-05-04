import os
from flask import Flask, request, render_template, make_response
import json
import csv
from io import StringIO
from bs4 import BeautifulSoup

app = Flask(__name__)

# Folder to store uploaded files
UPLOAD_FOLDER = "/tmp/uploads" if os.getenv("VERCEL") else "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Function to extract usernames from JSON file


def extract_usernames_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "relationships_following" in data:
            return [entry["string_list_data"][0]["value"] for entry in data["relationships_following"]]
        else:
            return [entry["string_list_data"][0]["value"] for entry in data]

# Function to extract usernames from HTML file


def extract_usernames_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        usernames = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if href.startswith("https://www.instagram.com/"):
                username = href.replace(
                    "https://www.instagram.com/", "").strip("/")
                if username and username not in usernames:
                    usernames.append(username)
        return usernames

# Function to determine file type and extract usernames
def process_file(file_path):
    if file_path.endswith(".json"):
        return extract_usernames_json(file_path)
    elif file_path.endswith(".html"):
        return extract_usernames_html(file_path)
    else:
        raise ValueError("File must be JSON or HTML!")


@app.route("/", methods=["GET", "POST"])
def index():
    not_following_back = []
    you_not_following_back = []
    followers_list = []
    following_list = []
    error_message = None

    if request.method == "POST":
        if "followers_file" not in request.files or "following_file" not in request.files:
            error_message = "Please upload both files (followers and following)!"
        else:
            followers_file = request.files["followers_file"]
            following_file = request.files["following_file"]

            if not followers_file.filename or not following_file.filename:
                error_message = "Please select both files!"
            else:
                followers_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], followers_file.filename)
                following_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], following_file.filename)
                followers_file.save(followers_path)
                following_file.save(following_path)

                try:
                    followers_list = sorted(process_file(
                        followers_path), key=str.lower)
                    following_list = sorted(process_file(
                        following_path), key=str.lower)
                    # Log 5 data pertama
                    print(f"Followers list: {followers_list[:5]}")
                    # Log 5 data pertama
                    print(f"Following list: {following_list[:5]}")

                    not_following_back = sorted(
                        list(set(following_list) - set(followers_list)), key=str.lower)
                    you_not_following_back = sorted(
                        list(set(followers_list) - set(following_list)), key=str.lower)
                    # Log 5 data pertama
                    print(f"Not following back: {not_following_back[:5]}")
                    # Log 5 data pertama
                    print(
                        f"You not following back: {you_not_following_back[:5]}")

                except Exception as e:
                    error_message = f"Error processing files: {str(e)}"

                if os.path.exists(followers_path):
                    os.remove(followers_path)
                if os.path.exists(following_path):
                    os.remove(following_path)

    return render_template("index.html",
                           not_following_back=not_following_back,
                           you_not_following_back=you_not_following_back,
                           followers_list=followers_list,
                           following_list=following_list,
                           error_message=error_message)

# Route to download CSV
@app.route("/download_csv/<list_type>", methods=["GET", "POST"])
def download_csv(list_type):
    # Retrieve the list from the form data (sent via POST)
    usernames = request.form.getlist("usernames")

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Username"])  # Header
    for username in usernames:
        writer.writerow([username])

    # Create response with CSV content
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={list_type}.csv"
    response.headers["Content-type"] = "text/csv"
    return response


if __name__ == '__main__':
    # Gunakan port dari Vercel, default ke 5000 jika di lokal
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)  # Tambahkan debug=True
