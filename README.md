# devops-toolbox-api

This project is a comprehensive toolbox API for DevOps teams, providing multiple utilities such as IP address calculations, public IP geolocation, SSL certificate information, and a temporary file sharing service. The API is built using **FastAPI** and can be easily deployed using **Docker** and **Docker Compose**.

## Features

1. **Get Client IP** (`/myip`): Retrieve the client's public IPv4 and IPv6 addresses.
2. **IP Calculator** (`/ipcalc/{ip}/{prefix}`): Get detailed network information based on the provided IP and prefix.
3. **IP Locator** (`/ip_locator/{ip}`): Geolocate a public IP address and return country, region, city, and ISP information.
4. **SSL Certificate Checker** (`/ssl_cert/{domain}`): Retrieve SSL certificate information for a given domain.
5. **File Sharing Service** (`/sharefile` & `/sharefile/{uuid}`): Upload a file for temporary sharing and automatically delete it after download or after 6 hours.

## Prerequisites

- **Docker**: Make sure Docker is installed on your system. You can install Docker from [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/).
- **Docker Compose**: Docker Compose is required to easily set up the application. Install instructions are available at [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/).
- **MaxMind Account**: Create an account at [MaxMind](https://www.maxmind.com) to download the GeoLite2 ASN and City databases.
  - Download the following databases:
    - **GeoLite2-City.mmdb**
    - **GeoLite2-ASN.mmdb**
  - Place these files in the `app` directory of this project.

## Setup and Installation

Follow these steps to set up and run the API locally:

1. **Clone the Repository**:

   ```sh
   git clone https://github.com/yourusername/devops-toolbox-api.git
   cd devops-toolbox-api
   ```

2. **Download MaxMind Databases**:

   - Download **GeoLite2-City.mmdb** and **GeoLite2-ASN.mmdb** from your MaxMind account. ( will managed automaticaly in the futur )
   - Place these databases in the `app` directory of the project:
     ```
     devops-toolbox-api/
     ├── app/
     │   ├── GeoLite2-City.mmdb
     │   ├── GeoLite2-ASN.mmdb
     ```

3. **Run Using Docker Compose**:

   - Use Docker Compose to build and run the project:
     ```sh
     docker-compose up
     ```
   - The API will be available at `http://localhost:8000`.

4. **API Documentation**:

   - Swagger UI is available at `http://localhost:8000/docs` for easy interaction with all endpoints.

## Environment Variables

The following environment variables can be configured to customize the behavior of the API:

- `UPLOAD_FOLDER`: Path to the folder where uploaded files will be temporarily stored (default is `./uploads`).
- `EXPIRATION_TIME_HOURS`: Number of hours before a shared file is automatically deleted (default is `6`).

## Usage

### Example Requests

- **Get Client IP**:
  ```sh
  curl -X GET "http://localhost:8000/myip"
  ```
- **IP Calculator**:
  ```sh
  curl -X GET "http://localhost:8000/ipcalc/192.168.1.0/24"
  ```
- **Upload File for Sharing**:
  ```sh
  curl -X POST "http://localhost:8000/sharefile" -F "file=@/path/to/your/file.txt"
  ```

## Cleanup Tasks

The API uses FastAPI's BackgroundTasks to manage file expiration. Uploaded files are automatically deleted after **6 hours** .

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

## Contributing

Feel free to submit pull requests or open issues to improve this project.

## Contact

For questions or suggestions, contact [[your-email@example.com](mailto\:your-email@example.com)].

