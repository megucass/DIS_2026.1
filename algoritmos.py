import numpy as np

MIN_DIV = 1e-15

def cgnr(H: np.ndarray, g: np.ndarray, max_iterations: int, tol: float, 
         min_iterations: int, lambda_reg: float = 0.0, logger=None) -> tuple:
    
    m, n = H.shape
  
    f = np.zeros(n, dtype=np.float64)
    g = g.flatten()
    r = g - H @ f
    z = H.T @ r - lambda_reg * f
    p = z.copy()
    norm_g = np.linalg.norm(g)
    initial_residual_norm = np.linalg.norm(r)
    
    number_iterations = 0

    if logger is not None:
        logger.info(f"CGNR Iniciado: tol={tol:.3e}, lambda_reg={lambda_reg:.3e}")

    for i in range(max_iterations):
        w = H @ p
        z_dot = np.dot(z, z)
        w_dot = np.dot(w, w) + lambda_reg * np.dot(p, p) + MIN_DIV
        alpha = z_dot / w_dot
        f_new = f + alpha * p
        r_new = r - alpha * w
        z_new = H.T @ r_new - lambda_reg * f_new
        z_new_dot = np.dot(z_new, z_new)
        beta = z_new_dot / (z_dot + MIN_DIV)
        p_new = z_new + beta * p
        # Métricas de erro
        current_residual_norm = np.linalg.norm(r_new)
        relative_error = current_residual_norm / (initial_residual_norm + MIN_DIV)
        if logger is not None:
            logger.info(
                f"Iteracao {i + 1}: erro relativo = {relative_error:.6e}, residuo = {current_residual_norm:.3e}"
            )
        # Transição de estados
        f, r, z, p = f_new, r_new, z_new, p_new
        number_iterations = i + 1
        if number_iterations >= min_iterations and relative_error < tol:
            if logger is not None:
                logger.info(f"Convergiu com erro relativo {relative_error:.2e} < {tol:.2e}")
            break
    final_residual = g - H @ f
    final_error = np.linalg.norm(final_residual) / (norm_g + MIN_DIV)
    
    return f, number_iterations, final_error

def cgne(H: np.ndarray, g: np.ndarray, max_iterations: int, tol: float, 
         min_iterations: int, lambda_reg: float = 0.0, logger=None) -> tuple:
    
    N = H.shape[1]
  
    f = np.zeros(N, 1)
    g = g.reshape(-1, 1)
    r = g - H @ f
    p = H.T @ r
    initial_residual_norm = np.linalg.norm(r)
    min_div = 1e-12
    final_iterations = 0

    if logger is not None:
        logger.info(f"CGNE Iniciado: tol={tol:.3e}, lambda_reg={lambda_reg:.3e}")

    for i in range(max_iterations):
        Hp = H @ p
        alpha_num = float(r.T @ r)
        alpha_den = float(Hp.T @ Hp) + min_div
        if alpha_den < min_div:
            break
        alpha = alpha_num / alpha_den
        f_new = f + alpha * p
        r_new = r - alpha * (H @ p)
        beta_num = float(r_new.T @ r_new)
        beta_den = float(r.T @ r) + min_div
        beta = beta_num / beta_den
        p_new = H.T @ r_new + beta * p

        current_residual_norm = np.linalg.norm(r_new)
        relative_error = current_residual_norm / (initial_residual_norm + min_div)
        if logger is not None:
            logger.info(
                f"Iteracao {i + 1}: erro relativo = {relative_error:.6e}, residuo = {current_residual_norm:.3e}"
            )
        f, r, p = f_new, r_new, p_new
        final_iterations = i + 1

        if final_iterations >= min_iterations and relative_error < tol:
            if logger is not None:
                logger.info(f"Convergiu com erro relativo {relative_error:.2e} < {tol:.2e}")
            break

    final_error = np.linalg.norm(g - H @ f) / (np.linalg.norm(g) + min_div)
    
    return f.flatten(), final_iterations, final_error