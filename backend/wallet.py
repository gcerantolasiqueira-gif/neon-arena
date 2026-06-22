from database import get_connection


INITIAL_BALANCE = 1000
BONUS_AMOUNT = 500
HOUSE_FEE_PERCENT = 5


def ensure_wallet(player_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT player_id, balance FROM wallets WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        if row:
            return dict(row)

        connection.execute(
            "INSERT INTO wallets (player_id, balance) VALUES (?, ?)",
            (player_id, INITIAL_BALANCE)
        )
        connection.execute("""
            INSERT INTO wallet_transactions (
                player_id, amount, balance_before, balance_after, type, room_code, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            INITIAL_BALANCE,
            0,
            INITIAL_BALANCE,
            "bonus_inicial",
            None,
            "Bônus inicial de Moedas Neon"
        ))
        connection.commit()

    return {
        "player_id": player_id,
        "balance": INITIAL_BALANCE
    }


def get_balance(player_id):
    wallet = ensure_wallet(player_id)
    balance = wallet["balance"]

    if balance <= 0:
        return refill_wallet(player_id, balance)

    return balance


def refill_wallet(player_id, current_balance=None):
    if current_balance is None:
        wallet = ensure_wallet(player_id)
        current_balance = wallet["balance"]

    if current_balance > 0:
        return current_balance

    amount = INITIAL_BALANCE - current_balance

    return add_transaction(
        player_id=player_id,
        amount=amount,
        transaction_type="recarga_automatica",
        room_code=None,
        description="Recarga automática para 1000 Moedas Neon"
    )


def add_bonus(player_id):
    return add_transaction(
        player_id=player_id,
        amount=BONUS_AMOUNT,
        transaction_type="bonus",
        room_code=None,
        description="Bônus de teste em Moedas Neon"
    )


def debit_entry(player_id, amount, room_code):
    if amount <= 0:
        return True, get_balance(player_id), None

    balance = get_balance(player_id)

    if balance < amount:
        return False, balance, "Saldo insuficiente"

    new_balance = add_transaction(
        player_id=player_id,
        amount=-amount,
        transaction_type="entrada_partida",
        room_code=room_code,
        description=f"Entrada em partida valendo {amount} Moedas Neon"
    )

    return True, new_balance, None


def pay_prize(winner_id, stake, room_code):
    if stake <= 0:
        return get_balance(winner_id)

    pot = stake * 2
    fee = round(pot * HOUSE_FEE_PERCENT / 100)
    prize = pot - fee

    return add_transaction(
        player_id=winner_id,
        amount=prize,
        transaction_type="premio_partida",
        room_code=room_code,
        description=f"Prêmio de {prize} Moedas Neon. Taxa fictícia: {fee}"
    )


def refund_entry(player_id, stake, room_code):
    if stake <= 0:
        return get_balance(player_id)

    return add_transaction(
        player_id=player_id,
        amount=stake,
        transaction_type="reembolso",
        room_code=room_code,
        description=f"Reembolso de partida cancelada: {stake} Moedas Neon"
    )


def add_transaction(player_id, amount, transaction_type, room_code, description):
    ensure_wallet(player_id)

    with get_connection() as connection:
        row = connection.execute(
            "SELECT balance FROM wallets WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        balance_before = row["balance"]
        balance_after = balance_before + amount

        connection.execute("""
            UPDATE wallets
            SET balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
        """, (balance_after, player_id))

        connection.execute("""
            INSERT INTO wallet_transactions (
                player_id, amount, balance_before, balance_after, type, room_code, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            amount,
            balance_before,
            balance_after,
            transaction_type,
            room_code,
            description
        ))

        connection.commit()

    return balance_after


def get_transactions(player_id, limit=12):
    ensure_wallet(player_id)

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT amount, balance_before, balance_after, type, room_code, description, created_at
            FROM wallet_transactions
            WHERE player_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (player_id, limit)).fetchall()

    return [dict(row) for row in rows]
