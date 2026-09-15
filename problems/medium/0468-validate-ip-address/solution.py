class Solution:
    def validIPAddress(self, queryIP):

        def is_ipv4(ip):
            parts = ip.split('.')

            if len(parts) != 4:
                return False

            for part in parts:
                if not part.isdigit():
                    return False

                if len(part) > 1 and part[0] == '0':
                    return False

                if int(part) > 255:
                    return False

            return True

        def is_ipv6(ip):
            parts = ip.split(':')

            if len(parts) != 8:
                return False

            hex_digits = '0123456789abcdefABCDEF'

            for part in parts:
                if len(part) < 1 or len(part) > 4:
                    return False

                for ch in part:
                    if ch not in hex_digits:
                        return False

            return True

        if '.' in queryIP:
            if is_ipv4(queryIP):
                return "IPv4"
            return "Neither"

        if ':' in queryIP:
            if is_ipv6(queryIP):
                return "IPv6"
            return "Neither"

        return "Neither"
