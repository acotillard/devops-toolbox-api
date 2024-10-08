from fastapi import FastAPI, Request, HTTPException, UploadFile, BackgroundTasks
import socket
import ipaddress
import geoip2.database
import ssl
import datetime
import uuid
import os
import asyncio
from fastapi.openapi.utils import get_openapi
import OpenSSL
from starlette.responses import FileResponse

UPLOAD_FOLDER = "./uploads"
EXPIRATION_TIME_HOURS = 6

app = FastAPI()

@app.get("/myip", summary="Get client IP address", description="Returns the client's public IPv4 and IPv6 addresses.")
async def get_my_ip(request: Request):
    client_host = request.client.host
    ipv4 = None
    ipv6 = None

    try:
        # Tentative de déterminer le type d'adresse
        addr_info = socket.getaddrinfo(client_host, None)
        for info in addr_info:
            family, _, _, _, sockaddr = info
            if family == socket.AF_INET:
                ipv4 = sockaddr[0]
            elif family == socket.AF_INET6:
                ipv6 = sockaddr[0]
    except Exception as e:
        print(f"Erreur lors de la détection de l'IP : {e}")
    
    return {"ipv4": ipv4, "ipv6": ipv6}

@app.get("/ipcalc/{ip}/{prefix}", summary="Calculate IP information", description="Returns detailed information about the given IP and prefix.")
async def ip_calc(ip: str, prefix: int):
    try:
        # Validation de l'adresse IP et du préfixe
        ip_obj = ipaddress.ip_address(ip)
        if not (0 <= prefix <= (32 if ip_obj.version == 4 else 128)):
            raise ValueError("Invalid prefix length for the given IP version.")

        network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
        netmask = str(network.netmask)
        broadcast = str(network.broadcast_address)
        network_address = str(network.network_address)
        hostmin = str(network.network_address + 1) if network.num_addresses > 2 else str(network.network_address)
        hostmax = str(network.broadcast_address - 1) if network.num_addresses > 2 else str(network.broadcast_address)
        hosts_net = network.num_addresses - 2 if network.num_addresses > 2 else network.num_addresses
    
        return {
            "prefix": f"{network_address}/{prefix}",
            "netmask": netmask,
            "network": network_address,
            "broadcast": broadcast,
            "hostmin": hostmin,
            "hostmax": hostmax,
            "hosts_net": hosts_net
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/ip_locator/{ip}", summary="Locate Public IP Address", description="Returns geographic information about the given public IP address, such as country, region, and ISP.")
async def ip_locator(ip: str):
    try:
        # Validation de l'adresse IP
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private:
            raise ValueError("The IP address must be public.")

        # Utiliser la base de données GeoIP pour la géolocalisation
        with geoip2.database.Reader('/app/GeoLite2-City.mmdb') as reader:
            response = reader.city(ip)
            location_data = {
                "ip": ip,
                "country": response.country.name,
                "region": response.subdivisions.most_specific.name,
                "city": response.city.name,
                "location": f"{response.location.latitude}, {response.location.longitude}"
            }

        # Utiliser la base de données GeoIP ASN pour obtenir l'organisation
        with geoip2.database.Reader('/app/GeoLite2-ASN.mmdb') as asn_reader:
            asn_response = asn_reader.asn(ip)
            location_data["org"] = asn_response.autonomous_system_organization

        return location_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except geoip2.errors.AddressNotFoundError:
        raise HTTPException(status_code=404, detail="IP address not found in the database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/ssl_cert/{domain}", summary="SSL Certificate Checker", description="Returns information about the SSL certificate for the given domain, such as validity, expiration date, and issuing authority.")
async def ssl_cert(domain: str):
    try:
        # Connexion SSL au domaine spécifié
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert)
                issuer = x509.get_issuer()
                issuer_name = "".join([f"/{name.decode()}={value.decode()}" for name, value in issuer.get_components()])
                expiration_date = datetime.datetime.strptime(x509.get_notAfter().decode("ascii"), "%Y%m%d%H%M%SZ")
                valid_from_date = datetime.datetime.strptime(x509.get_notBefore().decode("ascii"), "%Y%m%d%H%M%SZ")

                return {
                    "domain": domain,
                    "issuer": issuer_name,
                    "valid_from": valid_from_date.isoformat(),
                    "expires_on": expiration_date.isoformat(),
                    "is_valid": expiration_date > datetime.datetime.utcnow()
                }
    except socket.gaierror:
        raise HTTPException(status_code=404, detail="Domain not found.")
    except ssl.SSLError as e:
        raise HTTPException(status_code=500, detail=f"SSL error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/sharefile", summary="Share a File Temporarily", description="Upload a file to share temporarily. The file will be deleted after a default period of 6 hours.")
async def share_file(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        # Générer un UUID pour le fichier
        file_uuid = str(uuid.uuid4())
        original_filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, file_uuid)
        metadata_path = os.path.join(UPLOAD_FOLDER, f"{file_uuid}.meta")

        # Enregistrer le fichier sur le disque
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Enregistrer le nom du fichier original dans un fichier de métadonnées
        with open(metadata_path, "w") as meta_file:
            meta_file.write(original_filename)

        # Calculer l'heure d'expiration
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=EXPIRATION_TIME_HOURS)

        # Ajouter une tâche de suppression du fichier après expiration
        background_tasks.add_task(delete_expired_file, file_path, metadata_path, expiration_time)

        return {"uuid": file_uuid, "original_filename": original_filename, "message": "File uploaded successfully. It will expire in 6 hours."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")

@app.get("/sharefile/{uuid}", summary="Download Shared File", description="Download a file that was shared temporarily using its UUID. After download, the file will be deleted from the server.")
async def get_shared_file(uuid: str):
    file_path = os.path.join(UPLOAD_FOLDER, uuid)
    metadata_path = os.path.join(UPLOAD_FOLDER, f"{uuid}.meta")

    if not os.path.exists(file_path) or not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="File not found or expired.")

    # Récupérer le nom du fichier original
    with open(metadata_path, "r") as meta_file:
        original_filename = meta_file.read().strip()

    # Supprimer le fichier après téléchargement
    #os.remove(file_path)
    #os.remove(metadata_path)

    return FileResponse(file_path, filename=original_filename)

async def delete_expired_file(file_path: str, metadata_path: str, expiration_time: datetime.datetime):
    # Attendre jusqu'à l'expiration
    while datetime.datetime.utcnow() < expiration_time:
        await asyncio.sleep(60)  # Vérifier toutes les minutes
    # Supprimer le fichier et les métadonnées
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(metadata_path):
        os.remove(metadata_path)

# Custom Swagger UI Configuration
@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Super Tool API for DevOps",
        version="1.0.0",
        description="API that provides tools for DevOps, including the ability to retrieve client IP addresses and calculate IP information.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema
