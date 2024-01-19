from zksync2.eip712.struct import EIP712Struct
from zksync2.eip712.types import String, Uint, Address, Bytes


def make_domain(
    name=None, version=None, chainId=None, verifyingContract=None, salt=None
):
    """Helper method to create the standard EIP712Domain struct for you.

    Per the standard, if a value is not used then the parameter is omitted from the struct entirely.
    """

    if all(i is None for i in [name, version, chainId, verifyingContract, salt]):
        raise ValueError("At least one argument must be given.")

    class EIP712Domain(EIP712Struct):
        pass

    kwargs = dict()
    if name is not None:
        EIP712Domain.name = String()
        kwargs["name"] = str(name)
    if version is not None:
        EIP712Domain.version = String()
        kwargs["version"] = str(version)
    if chainId is not None:
        EIP712Domain.chainId = Uint(256)
        kwargs["chainId"] = int(chainId)
    if verifyingContract is not None:
        EIP712Domain.verifyingContract = Address()
        kwargs["verifyingContract"] = verifyingContract
    if salt is not None:
        EIP712Domain.salt = Bytes(32)
        kwargs["salt"] = salt

    return EIP712Domain(**kwargs)
