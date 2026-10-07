import pytest

from app.crawler.ssrf import UnsafeURLError, is_ip_allowed, normalize_url


@pytest.mark.parametrize("ip", ["127.0.0.1", "0.0.0.0", "10.1.2.3", "172.16.5.4", "172.31.255.255", "192.168.1.1", "169.254.169.254",
                                "100.64.0.1", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1", "::ffff:10.0.0.1", "224.0.0.1", "255.255.255.255"])
def test_private_ips_blocked(ip):
    assert not is_ip_allowed(ip)


@pytest.mark.parametrize("ip", ["8.8.8.8", "77.88.55.88", "2a02:6b8::2:242"])
def test_public_ips_allowed(ip):
    assert is_ip_allowed(ip)


@pytest.mark.parametrize("url", ["http://localhost/", "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data", "http://10.0.0.5",
                                 "http://192.168.0.1/admin", "http://[::1]/", "http://2130706433/", "http://0x7f000001/", "ftp://example.ru",
                                 "file:///etc/passwd", "http://user:pass@example.ru/", "http://example.ru:8080/", "http://intranet/",
                                 "http://router.local/", "gopher://example.ru"])
def test_unsafe_urls_rejected(url):
    with pytest.raises(UnsafeURLError):
        normalize_url(url)


def test_normalize_adds_scheme_and_idna():
    assert normalize_url("example.ru") == "https://example.ru/"
    assert normalize_url("https://пример.рф/путь?x=1#a").startswith("https://xn--e1afmkfd.xn--p1ai/")
