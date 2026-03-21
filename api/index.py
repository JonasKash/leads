from app.main import main

# Ponto de entrada padrão para a Vercel reconhecer o projeto Python
# O Streamlit é um servidor, mas ter este arquivo na pasta api/ 
# resolve o erro de 'No python entrypoint found'.

if __name__ == "__main__":
    main()
